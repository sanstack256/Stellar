from __future__ import annotations
import re
from pathlib import Path

_TEST_PATTERNS=("test_*.py","*_test.py","*.test.ts","*.spec.ts","*.test.js","*.spec.js","*.test.tsx","*.spec.tsx","*_test.go","*_test.rs")

def inventory(repo: str) -> list[dict]:
    root=Path(repo); files=[]
    seen=set()
    for pattern in _TEST_PATTERNS:
        for p in root.rglob(pattern):
            if any(part in {".git","node_modules","dist","build","__pycache__"} for part in p.parts): continue
            if p in seen: continue
            seen.add(p)
            text=p.read_text(errors="replace")
            names=[]
            for line in text.splitlines():
                m=re.search(r"(?:def|it|test)\s+([A-Za-z0-9_$.-]+)",line)
                if m: names.append(m.group(1))
            files.append({"test_id":p.name,"file":str(p.relative_to(root)),"description":" ".join(names[:12]) or p.name,"text":text[:12000]})
    return files

def rank(tests, affected, changed_entities):
    context=[]
    for e in list(changed_entities)+[x for x in affected]:
        context += re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}",str(e))
    tokens={x.lower() for x in context}
    out=[]
    for t in tests:
        hay=(t["file"]+" "+t["description"]+" "+t.get("text","")).lower()
        overlap=sum(1 for token in tokens if token in hay)
        score=min(100, overlap*12)
        if any(str(a.get("file") or "").lower().split("/")[-1].split(".")[0] in hay for a in affected): score=min(100,score+30)
        if score:
            priority="critical" if score>=70 else "recommended" if score>=35 else "optional"
            out.append({"test_id":t["test_id"],"file":t["file"],"priority":priority,"relevance_score":score,"reason":f"matched {overlap} change/impact token(s)"})
    return sorted(out,key=lambda x:(-x["relevance_score"],x["file"]))[:10]
