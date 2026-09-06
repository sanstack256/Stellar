from repo_manager import validate_url, _slug
import pytest

def test_validate_public_https_url():
    assert validate_url("https://github.com/example/project.git").startswith("https://")

def test_reject_embedded_credentials():
    with pytest.raises(ValueError): validate_url("https://user:pass@github.com/example/project.git")

def test_slug_stable():
    assert _slug("https://github.com/example/project.git").startswith("project-")
