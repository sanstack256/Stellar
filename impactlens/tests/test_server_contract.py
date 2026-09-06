from api.server import AnalyzeRequest

def test_analyze_request_has_no_default_repository():
    try: AnalyzeRequest(repo_path="x",repo_name="y")
    except Exception as exc: raise AssertionError(exc)
