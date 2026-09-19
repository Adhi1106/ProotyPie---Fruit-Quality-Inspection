from pathlib import Path
from experiments.train_expanded import split_records, make_model
import pytest

def test_stratified_split():
    records=[{'path':str(i),'class':c,'sha256':f'{c}{i}'} for c in ['A','B'] for i in range(10)]
    train,val=split_records(records,seed=42)
    assert len(train)==16 and len(val)==4
    assert set(x['sha256'] for x in train).isdisjoint(x['sha256'] for x in val)
    assert {x['class'] for x in val}=={'A','B'}

@pytest.mark.parametrize('activation',['relu','sigmoid','tanh','leaky_relu'])
def test_model_shape_and_optimizer(activation):
    m=make_model(activation,.01,131)
    assert m.input_shape==(None,32,32,3)
    assert m.output_shape==(None,131)
    assert m.optimizer.__class__.__name__=='SGD'
