"""Pinned 131-class Fruits-360 experiment. Never overwrites the small pilot.
Run: python experiments/train_expanded.py --run --epochs 8
CPU threads bounded; each configuration checkpointed independently.
"""
from __future__ import annotations
import os
os.environ.setdefault('TF_NUM_INTRAOP_THREADS','2')
os.environ.setdefault('TF_NUM_INTEROP_THREADS','2')
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
import argparse,csv,hashlib,json,random,time,zipfile
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image
import tensorflow as tf
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,confusion_matrix
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/expanded'
CACHE=Path(os.environ.get('FRUITS360_CACHE',str(ROOT.parent.parent/'datasets/fruits360-131')))
COMMIT='ffda2d14eada57a0c5537700190b309cfea2e120'
SEED=20260919
ACTIVATIONS=['relu','sigmoid','tanh','leaky_relu']
RATES=[.001,.01,.1]
SIZE=32
BATCH=128

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2));temp.replace(path)

def split_records(records,seed=SEED):
    groups=defaultdict(list)
    for r in records:groups[r['class']].append(r)
    rng=random.Random(seed);train=[];val=[]
    for label in sorted(groups):
        rows=groups[label].copy();rng.shuffle(rows);n=max(1,round(len(rows)*.2));val+=rows[:n];train+=rows[n:]
    return train,val

def activation(name):
    return tf.keras.layers.LeakyReLU(negative_slope=.1) if name=='leaky_relu' else tf.keras.layers.Activation(name)

def make_model(name,lr,nclasses):
    if name not in ACTIVATIONS:raise ValueError(name)
    model=tf.keras.Sequential([tf.keras.Input((SIZE,SIZE,3)),tf.keras.layers.Conv2D(8,3,padding='same'),activation(name),tf.keras.layers.MaxPooling2D(),tf.keras.layers.Conv2D(16,3,padding='same'),activation(name),tf.keras.layers.MaxPooling2D(),tf.keras.layers.Flatten(),tf.keras.layers.Dense(64),activation(name),tf.keras.layers.Dense(nclasses,activation='softmax')])
    model.compile(optimizer=tf.keras.optimizers.SGD(learning_rate=lr,momentum=0.0),loss='sparse_categorical_crossentropy',metrics=['accuracy'])
    return model

def prepare(cap=0):
    source=CACHE/f'Fruit-Images-Dataset-{COMMIT}'
    if not (source/'Training').is_dir():
        with zipfile.ZipFile(CACHE/'source.zip') as z:
            for item in z.infolist():
                rel=Path(item.filename)
                if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe archive path')
                if len(rel.parts)>1 and rel.parts[1] in {'Training','Test','LICENSE','readme.md'}:z.extract(item,CACHE)
    names=sorted(p.name for p in (source/'Training').iterdir() if p.is_dir())
    assert len(names)==131, f'Expected pinned 131 classes, got {len(names)}'
    records={};seen={};excluded=[];original={}
    for split in ['Training','Test']:
        rows=[];original[split]=0
        for name in names:
            paths=sorted((source/split/name).glob('*.jpg'));original[split]+=len(paths)
            if cap and split=='Training':paths=paths[:cap]
            for p in paths:
                digest=hashlib.sha256(p.read_bytes()).hexdigest()
                if digest in seen:
                    excluded.append({'path':str(p.relative_to(source)),'duplicate_of':seen[digest]});continue
                seen[digest]=str(p.relative_to(source))
                rows.append({'path':str(p.relative_to(source)),'class':name,'sha256':digest})
        records[split]=rows
    train,val=split_records(records['Training']);test=records['Test']
    save(OUT/'duplicate_exclusions.json',excluded)
    with (OUT/'split_manifest.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['split','path','class','sha256']);writer.writeheader()
        for split,rows in [('train',train),('validation',val),('test',test)]:
            for r in rows:writer.writerow({'split':split,**r})
    def load(rows):
        X=np.empty((len(rows),SIZE,SIZE,3),dtype='float32');y=np.empty(len(rows),dtype='int32');lookup={n:i for i,n in enumerate(names)}
        for i,r in enumerate(rows):
            with Image.open(source/r['path']) as im:X[i]=np.asarray(im.convert('RGB').resize((SIZE,SIZE),Image.Resampling.BILINEAR),dtype='float32')/255
            y[i]=lookup[r['class']]
        return X,y
    return names,original,excluded,train,val,test,load(train),load(val),load(test)

def dataset(x,y,train=False):
    d=tf.data.Dataset.from_tensor_slices((x,y))
    if train:d=d.shuffle(len(y),seed=SEED,reshuffle_each_iteration=True)
    opts=tf.data.Options();opts.threading.private_threadpool_size=2;opts.experimental_deterministic=True
    return d.batch(BATCH).with_options(opts).prefetch(1)

def metrics(y,p):
    pred=p.argmax(1);pr,re,f,_=precision_recall_fscore_support(y,pred,average='macro',zero_division=0)
    return dict(accuracy=float(accuracy_score(y,pred)),precision_macro=float(pr),recall_macro=float(re),f1_macro=float(f))

class Progress(tf.keras.callbacks.Callback):
    def __init__(self,tag):super().__init__();self.tag=tag;self.start=time.monotonic()
    def on_epoch_end(self,epoch,logs=None):
        save(OUT/'progress.json',{'state':'training','configuration':self.tag,'epoch_completed':epoch+1,'elapsed_seconds':time.monotonic()-self.start,'metrics':{k:float(v)for k,v in (logs or {}).items()}})
        print(self.tag,epoch+1,logs,flush=True)

def run(epochs=8,cap=0):
    began=time.monotonic();OUT.mkdir(parents=True,exist_ok=True);save(OUT/'progress.json',{'state':'preparing dataset'})
    names,original,excluded,tr,va,te,(xt,yt),(xv,yv),(xe,ye)=prepare(cap)
    train=dataset(xt,yt,True);valid=dataset(xv,yv);test=dataset(xe,ye)
    scope={'dataset':'Fruits-360 2020.05.18.0 / 131-class snapshot','source_commit':COMMIT,'source_url':'https://github.com/Horea94/Fruit-Images-Dataset','classes':names,'source_training_count':original['Training'],'source_test_count':original['Test'],'training_samples':len(tr),'validation_samples':len(va),'test_samples':len(te),'sampling':'All single-fruit Training and Test JPGs; exact duplicates excluded' if not cap else f'At most {cap} Training images per class; all Test JPGs; exact duplicates excluded','duplicate_exclusions':len(excluded),'seed':SEED,'epochs':epochs,'batch_size':BATCH,'image_size':SIZE,'optimizer':'SGD, momentum=0','architecture':'Conv2D(8,3,same), activation, MaxPool2D, Conv2D(16,3,same), activation, MaxPool2D, Flatten, Dense(64), activation, Dense(131,softmax)'}
    save(OUT/'scope.json',scope);save(OUT/'class_names.json',names)
    results=[];best=None
    for name in ACTIVATIONS:
        for lr in RATES:
            tag=f'{name}_{lr:g}';file=OUT/f'run_{tag}.json'
            if file.exists():
                result=json.loads(file.read_text())
                if result['epochs']!=epochs:raise RuntimeError('Resume epoch mismatch')
            else:
                tf.keras.backend.clear_session();tf.keras.utils.set_random_seed(SEED);tf.config.experimental.enable_op_determinism();m=make_model(name,lr,len(names));t=time.monotonic()
                h=m.fit(train,validation_data=valid,epochs=epochs,verbose=0,callbacks=[Progress(tag)]).history
                p=m.predict(valid,verbose=0);result={'activation':name,'learning_rate':lr,'epochs':epochs,'history':{k:[float(v)for v in vals]for k,vals in h.items()},'validation_metrics':metrics(yv,p),'training_seconds':time.monotonic()-t}
                m.save(OUT/f'model_{tag}.keras');save(file,result)
            results.append(result)
            score=(result['validation_metrics']['f1_macro'],result['validation_metrics']['accuracy'])
            if best is None or score>best[0]:best=(score,tag,result)
            save(OUT/'partial_results.json',{'scope':scope,'experiments':results})
    # Evaluate selected saved checkpoint; no refit and no test-based selection.
    model=tf.keras.models.load_model(OUT/f'model_{best[1]}.keras');p=model.predict(test,verbose=0);pred=p.argmax(1)
    pr,re,f,support=precision_recall_fscore_support(ye,pred,labels=range(len(names)),zero_division=0)
    summary={'scope':scope,'experiments':results,'best_config':{'activation':best[2]['activation'],'learning_rate':best[2]['learning_rate'],'selection_metric':'validation macro F1; accuracy tie-break; saved train-only checkpoint, no refit'},'test_metrics':metrics(ye,p),'test_confusion_matrix':confusion_matrix(ye,pred,labels=range(len(names))).tolist(),'per_class':[{'class':n,'precision':float(pr[i]),'recall':float(re[i]),'f1':float(f[i]),'support':int(support[i])}for i,n in enumerate(names)],'elapsed_seconds':time.monotonic()-began}
    model.save(OUT/'best_model.keras');np.savez_compressed(OUT/'test_predictions.npz',true=ye,predicted=pred,probabilities=p);save(OUT/'summary.json',summary);save(OUT/'progress.json',{'state':'completed','configurations':len(results),'elapsed_seconds':summary['elapsed_seconds']});print(json.dumps({'best':summary['best_config'],'test':summary['test_metrics']}),flush=True);return summary
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--epochs',type=int,default=8);ap.add_argument('--cap',type=int,default=0);args=ap.parse_args()
    if args.run:
        run(args.epochs,args.cap)
        import subprocess,sys
        subprocess.run([sys.executable,str(ROOT/'scripts/annotate_divergence.py')],check=True)
