"""
FastAPI app for Stellar - AI Codebase Impact & Risk Engine

Request flow:
  GitHub webhook / UI -> POST /analyze/{commit} -> Impact Report JSON

Run:
    uvicorn api.server:app --reload --port 8000
"""
from __future__ import annotations
import logging
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from api.orchestrator import run_analysis, AnalysisError
from repo_manager import clone as clone_repo, list_repos
from integrations.entire import verify as verify_entire
from integrations.databricks import enabled as databricks_enabled

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("stellar")

BASE_DIR = Path(__file__).resolve().parent.parent

_SAFE_REF_RE = re.compile(r"^(?!-)[A-Za-z0-9._/\-]{1,200}$")

app = FastAPI(title="Stellar", description="AI Codebase Impact & Risk Engine")

_cors = [x.strip() for x in (os.getenv("CORS_ORIGINS", "*")).split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_cors, allow_methods=["GET", "POST"], allow_headers=["*"], allow_credentials=False)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_id = uuid.uuid4().hex[:8]
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(f"[{req_id}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
    response.headers["X-Request-Id"] = req_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = uuid.uuid4().hex[:8]
    logger.exception(f"[{req_id}] unhandled error on {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "internal error", "request_id": req_id})


class AnalyzeRequest(BaseModel):
    repo_path: str
    repo_name: str
    semantic_base: str | None = None

    @field_validator("repo_name")
    @classmethod
    def _safe_repo_name(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9._\-]{1,100}$", v):
            raise ValueError("repo_name must be alphanumeric plus . _ -")
        return v


def _resolve_repo_path(repo_path: str) -> Path:
    configured = os.getenv("STELLAR_REPO_ROOT", os.getenv("IMPACTLENS_REPO_ROOT", "")).strip()
    root = Path(configured).expanduser().resolve() if configured else BASE_DIR.resolve()
    raw = Path(repo_path).expanduser()
    candidate = (raw if raw.is_absolute() else root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(400, "repo_path must stay within repository root")
    return candidate


class CloneRequest(BaseModel):
    repo_url: str
    name: str | None = None


@app.post("/repos/clone")
def clone_repository(body: CloneRequest):
    try:
        return clone_repo(body.repo_url, body.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "git clone failed").strip()[-1000:]
        raise HTTPException(400, detail)
    except Exception as exc:
        raise HTTPException(500, f"repository import failed: {exc}")


@app.get("/repos")
def repositories():
    return {"repos": list_repos()}


@app.post("/analyze/{commit}")
def analyze(commit: str, body: AnalyzeRequest, x_api_key: str | None = Header(default=None)):
    required_key = os.getenv("STELLAR_API_KEY", os.getenv("IMPACTLENS_API_KEY"))
    if required_key and x_api_key != required_key:
        raise HTTPException(401, "invalid API key")
    if not _SAFE_REF_RE.match(commit):
        raise HTTPException(400, "invalid commit/ref format")

    repo_path = _resolve_repo_path(body.repo_path)
    if not repo_path.exists():
        raise HTTPException(404, f"repo not found: {body.repo_path}")
    if not (repo_path / ".git").exists():
        raise HTTPException(400, f"{body.repo_path} is not a git repository")

    try:
        report = run_analysis(str(repo_path), body.repo_name, commit, semantic_base=body.semantic_base)
    except AnalysisError as exc:
        raise HTTPException(400, str(exc))
    return report


@app.get("/commits")
def list_commits(repo_path: str, limit: int = 20):
    path = _resolve_repo_path(repo_path)
    if not path.exists() or not (path / ".git").exists():
        raise HTTPException(404, f"not a git repo: {repo_path}")
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "log", f"-{max(1, min(limit, 100))}", "--pretty=%H|%s"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise HTTPException(400, f"git log failed: {exc.stderr}")
    commits = []
    for line in out.splitlines():
        if "|" in line:
            sha, subject = line.split("|", 1)
            commits.append({"sha": sha, "subject": subject})
    return {"commits": commits}


@app.get("/health")
def health():
    return {"status": "ok", "data_plane": "databricks" if databricks_enabled() else "disabled", "entire_required": True}


@app.get("/health/integrations")
def integration_health():
    result = {"entire": {"required": True}, "databricks": {"enabled": databricks_enabled()}}
    configured = os.getenv("STELLAR_REPO_ROOT", os.getenv("IMPACTLENS_REPO_ROOT", "")).strip()
    if configured:
        try:
            result["entire"].update(verify_entire(configured))
        except Exception as exc:
            result["entire"]["error"] = str(exc)
    if databricks_enabled():
        try:
            from integrations.databricks import DatabricksStore
            DatabricksStore().connect().close()
            result["databricks"]["available"] = True
        except Exception as exc:
            result["databricks"]["error"] = str(exc)
    return result


dashboard_dir = BASE_DIR / "dashboard"
if dashboard_dir.exists():
    app.mount("/", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")
