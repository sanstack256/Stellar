import os
from repo_manager import validate_url

def test_repo_urls_require_https_without_credentials():
    assert validate_url("https://github.com/org/repo.git")
    for url in ("http://github.com/org/repo.git","https://user:pass@github.com/org/repo.git"):
        try: validate_url(url)
        except ValueError: pass
        else: raise AssertionError(url)
