"""Independently verify completed experiment metrics and split provenance."""
from pathlib import Path
import csv,json
import numpy as np
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,confusion_matrix
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'artifacts/expanded'
s=json.loads((p/'summary.json').read_text())
assert len(s['experiments'])==12
assert {(r['activation'],r['learning_rate'])for r in s['experiments']}=={(a,l)for a in ['relu','sigmoid','tanh','leaky_relu']for l in [.001,.01,.1]}
assert len(s['scope']['classes'])==131
for r in s['experiments']:
 assert all(len(r['history'][k])==s['scope']['epochs']for k in ['loss','accuracy','val_loss','val_accuracy'])
 assert r.get('status')=='diverged' or all(np.isfinite(v)for vals in r['history'].values()for v in vals)
selected=max([r for r in s['experiments'] if r.get('status')!='diverged'],key=lambda r:(r['validation_metrics']['f1_macro'],r['validation_metrics']['accuracy']))
assert selected['activation']==s['best_config']['activation']
assert selected['learning_rate']==s['best_config']['learning_rate']
a=np.load(p/'test_predictions.npz');true=a['true'];pred=a['predicted']
assert len(true)==s['scope']['test_samples'];assert np.array_equal(pred,a['probabilities'].argmax(1))
pr,re,f,_=precision_recall_fscore_support(true,pred,average='macro',zero_division=0)
measured=dict(accuracy=accuracy_score(true,pred),precision_macro=pr,recall_macro=re,f1_macro=f)
assert all(abs(measured[k]-s['test_metrics'][k])<1e-10 for k in measured)
assert np.array_equal(confusion_matrix(true,pred,labels=range(131)),s['test_confusion_matrix'])
rows=list(csv.DictReader((p/'split_manifest.csv').open()))
sets={k:{r['sha256']for r in rows if r['split']==k}for k in ['train','validation','test']}
assert not sets['train']&sets['validation'] and not sets['train']&sets['test'] and not sets['validation']&sets['test']
result={'verified':True,'configurations':12,'classes':131,'split_counts':{k:len(v)for k,v in sets.items()},'test_metrics_recomputed':measured,'best_config':s['best_config']}
(p/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
