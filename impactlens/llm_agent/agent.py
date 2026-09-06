"""Evidence-grounded reasoning. Provider and model are configuration, never product constants."""
from __future__ import annotations
import json, os
from llm_agent.prompts import SYSTEM_PROMPT, build_user_prompt

def _required(name):
    value=os.getenv(name,"").strip()
    if not value: raise RuntimeError(f"{name} is required")
    return value

def _call_openai_compatible(context):
    from openai import OpenAI
    base=_required("LLM_BASE_URL").rstrip("/")
    key=_required("LLM_API_KEY")
    model=_required("LLM_MODEL")
    client=OpenAI(api_key=key,base_url=base)
    response=client.chat.completions.create(model=model,temperature=0.1,max_tokens=int(os.getenv("LLM_MAX_TOKENS","1800")),messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":build_user_prompt(context)}])
    text=response.choices[0].message.content.strip(); text=text[4:] if text.startswith("json") else text
    text=text.strip("`")
    out=json.loads(text); out["engine"]="configured-model-serving"; return out

def _fallback_report(context):
    return {"what_changed":f"Changed entities: {', '.join(context['changed_entities']) or 'unresolved at symbol level'}","what_could_be_affected":[a["entity_id"] for a in context["affected_entities"][:10]],"what_to_test":[{"test":t["test_id"],"priority":t["priority"],"reason":t["reason"]} for t in context["recommended_tests"]],"what_might_be_missed":[{"concern":m["entity_id"],"reason":m["reason"]} for m in context["candidate_missed_risks"]],"confidence":0.0,"engine":"unverified-fallback"}

def analyze(context):
    try:
        return _call_openai_compatible(context)
    except Exception as exc:
        if os.getenv("ALLOW_UNVERIFIED_LLM_FALLBACK","false").lower() in {"1","true","yes","on"}:
            out=_fallback_report(context); out["engine_error"]=str(exc); return out
        raise
