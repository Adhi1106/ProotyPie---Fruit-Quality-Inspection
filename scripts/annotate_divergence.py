"""Label non-finite experimental outcomes; do not invent usable metrics."""
from pathlib import Path
import json, math
root=Path(__file__).resolve().parents[1];p=root/'artifacts/expanded/summary.json'
s=json.loads(p.read_text())
for r in s['experiments']:
    bad={k:[i+1 for i,v in enumerate(vals) if v is None or not math.isfinite(v)] for k,vals in r['history'].items()}
    bad={k:v for k,v in bad.items() if v}
    if bad:
        r['status']='diverged';r['nonfinite_epochs']=bad
        r['validation_metrics']={k:None for k in r['validation_metrics']}
        r['history']={k:[v if v is not None and math.isfinite(v) else None for v in vals] for k,vals in r['history'].items()}
        r['note']='Loss became non-finite. Argmax of invalid model outputs is not a valid evaluation; metrics are deliberately unavailable. Raw run checkpoint and logs retained separately.'
    else:r['status']='completed'
p.write_text(json.dumps(s,indent=2,allow_nan=False))
print([(r['activation'],r['learning_rate'],r['status']) for r in s['experiments']])
