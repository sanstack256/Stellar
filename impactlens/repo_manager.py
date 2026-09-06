from __future__ import annotations
import hashlib, os, re, subprocess
from pathlib import Path
from urllib.parse import urlparse

_URL_RE=re.compile(r"^https://[^\s]+$",re.I)

BASE_DIR = Path(__file__).resolve().parent

def root() -> Path:
    value = os.getenv("STELLAR_REPO_ROOT", os.getenv("IMPACTLENS_REPO_ROOT", "")).strip()
    if value:
        p = Path(value).expanduser().resolve()
    else:
        p = (BASE_DIR / "repos").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def _slug(url: str) -> str:
    parsed=urlparse(url); name=Path(parsed.path.rstrip("/")).name or "repo"
    name=re.sub(r"\.git$","",name); name=re.sub(r"[^A-Za-z0-9._-]+","-",name)[:50] or "repo"
    return f"{name}-{hashlib.sha256(url.encode()).hexdigest()[:10]}"

def validate_url(url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    elif not url.startswith("http://") and not url.startswith("https://") and "github.com" in url:
        url = "https://" + url
    parsed = urlparse(url)
    if not _URL_RE.match(url) or parsed.username or parsed.password:
        raise ValueError("repo_url must be HTTPS without embedded credentials")
    return url

def clone(url: str, name: str|None=None) -> dict:
    url = validate_url(url)
    base = root()
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name or _slug(url))[:70]
    dest = (base / slug).resolve()
    dest.relative_to(base)
    token = os.getenv("GIT_TOKEN", "").strip()
    if (dest / ".git").exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "--all", "--prune"], check=True, capture_output=True, text=True, timeout=180)
    else:
        cmd = ["git"]
        if token:
            cmd += ["-c", f"http.extraheader=Authorization: Bearer {token}"]
        cmd += ["clone", "--no-tags", url, str(dest)]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=15).stdout.strip()
    path_str = str(dest.relative_to(BASE_DIR)) if dest.is_relative_to(BASE_DIR) else str(dest)
    return {"repo_path": path_str, "repo_name": dest.name, "head": head, "url": url}

def list_repos() -> list[dict]:
    base=root(); out=[]
    for p in sorted(base.iterdir()):
        if (p/".git").exists():
            head=subprocess.run(["git","-C",str(p),"rev-parse","HEAD"],capture_output=True,text=True,timeout=10).stdout.strip()
            out.append({"repo_path":str(p),"repo_name":p.name,"head":head})
    return out
