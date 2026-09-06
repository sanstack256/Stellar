from risk_engine.scorer import score_change

def test_risk_has_no_business_specific_modules():
    r=score_change(["module.Service.run"],{"caller.Handler.run":{"depth":1,"changed_entity":"module.Service.run"}},set(),[],{"prompt":"intent"},graph=[{"symbol":"module.Service.run","callers":[{"entity_id":"caller.Handler.run"}]}])
    assert 0 <= r["risk_score"] <= 100
    assert "payments" not in " ".join(r["risk_reasons"]).lower()
