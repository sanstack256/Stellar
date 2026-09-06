"""Evidence-grounded LLM layer.

Priority order: Databricks Model Serving -> Anthropic -> deterministic fallback.
When MLflow is configured, the analysis is traced without changing the core flow.
"""
from __future__ import annotations
import json, os
from llm_agent.prompts import SYSTEM_PROMPT, build_user_prompt


def _databricks_enabled():
    return os.getenv("DATABRICKS_LLM_ENABLED", os.getenv("DATABRICKS_ENABLED","false")).lower() in {"1","true","yes","on"} and bool(os.getenv("DATABRICKS_LLM_ENDPOINT"))

def _call_databricks(context:dict)->dict:
    from openai import OpenAI
    host=os.getenv("DATABRICKS_WORKSPACE_URL", "").rstrip("/")
    token=os.getenv("DATABRICKS_TOKEN")
    if not host or not token: raise RuntimeError("Databricks workspace URL/token missing")
    client=OpenAI(api_key=token, base_url=f"{host}/serving-endpoints")
    response=client.chat.completions.create(model=os.environ["DATABRICKS_LLM_ENDPOINT"],temperature=0.1,max_tokens=1800,
        messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":build_user_prompt(context)}])
    text=response.choices[0].message.content.strip()
    if text.startswith("```"):
        text=text.strip("`"); text=text[4:] if text.startswith("json") else text
    out=json.loads(text); out["engine"]="databricks-model-serving"; return out

def _call_claude(context):
    import anthropic
    client=anthropic.Anthropic()
    message=client.messages.create(model=os.getenv("ANTHROPIC_MODEL","claude-sonnet-4-6"),max_tokens=1800,system=SYSTEM_PROMPT,messages=[{"role":"user","content":build_user_prompt(context)}])
    text="".join(b.text for b in message.content if b.type=="text").strip()
    if text.startswith("```"): text=text.strip("`"); text=text[4:] if text.startswith("json") else text
    out=json.loads(text); out["engine"]="anthropic"; return out

def _fallback_report(context):
    return {"what_changed":f"{', '.join(context['changed_entities']) or 'Code'} changed in commit {context['commit']['subject']}",
            "what_could_be_affected":[a["entity_id"] for a in context["affected_entities"][:10]],
            "what_to_test":[{"test":t["test_id"],"priority":t["priority"],"reason":t["reason"]} for t in context["recommended_tests"]],
            "what_might_be_missed":[{"concern":m["entity_id"],"reason":m["reason"]} for m in context["candidate_missed_risks"]],
            "confidence":0.72,"engine":"evidence-fallback"}

def analyze(context):
    try:
        if _databricks_enabled(): return _call_databricks(context)
        if os.getenv("ANTHROPIC_API_KEY"): return _call_claude(context)
    except Exception as exc:
        fallback=_fallback_report(context); fallback["engine_error"]=str(exc); return fallback
    return _fallback_report(context)
