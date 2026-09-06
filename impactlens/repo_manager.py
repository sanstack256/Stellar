from __future__ import annotations
import hashlib, os, re, shutil, subprocess
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
REPOS_DIR = BASE_DIR / "repos"
REPOS_DIR.mkdir(exist_ok=True)

_URL_RE = re.compile(r"^https?://[^\s]+$", re.I)


def _slug(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path.rstrip("/")).name or "repo"
    name = re.sub(r"\.git$", "", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)[:50] or "repo"
    return f"{name}-{hashlib.sha1(url.encode()).hexdigest()[:8]}"


def validate_url(url: str) -> str:
    url = url.strip()
    if not _URL_RE.match(url):
        raise ValueError("repo_url must be an HTTPS/HTTP Git URL")
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise ValueError("embedded Git credentials are not allowed; use a credential helper/token")
    return url


def clone(url: str, name: str | None = None) -> dict:
    url = validate_url(url)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name or _slug(url))[:70]
    dest = REPOS_DIR / slug
    if (dest / ".git").exists():
        # Fetch the latest refs for repeat analyses without recloning.
        subprocess.run(["git", "-C", str(dest), "fetch", "--all", "--prune"], capture_output=True, text=True, timeout=180)
    else:
        if dest.exists(): shutil.rmtree(dest)
        cmd=["git"]
        token=os.getenv("GIT_TOKEN", "").strip()
        if token:
            cmd += ["-c", f"http.extraheader=Authorization: Bearer {token}"]
        cmd += ["clone", "--no-tags", url, str(dest)]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=15).stdout.strip()
    return {"repo_path": str(dest.relative_to(BASE_DIR)), "repo_name": dest.name, "head": head, "url": url}


def list_repos() -> list[dict]:
    out=[]
    for p in sorted(REPOS_DIR.iterdir() if REPOS_DIR.exists() else []):
        if (p / ".git").exists():
            try:
                head=subprocess.run(["git","-C",str(p),"rev-parse","HEAD"],capture_output=True,text=True,timeout=10).stdout.strip()
            except Exception: head=""
            out.append({"repo_path":str(p.relative_to(BASE_DIR)),"repo_name":p.name,"head":head})
    return out
