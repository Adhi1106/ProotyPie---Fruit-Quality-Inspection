from pathlib import Path
import nbformat
from nbclient import NotebookClient
r=Path(__file__).resolve().parents[1];p=r/'notebooks/Fruits360_Expanded_Experiments.ipynb'
nb=nbformat.read(p,as_version=4)
nb.cells.insert(-2,nbformat.v4.new_markdown_cell('## Interpretation and numerical stability\n\nTanh at learning rate 0.1 was selected by validation macro F1. Its official-Test accuracy is 93.23%, with macro F1 92.74%. Leaky ReLU at 0.1 developed non-finite loss from epoch 6; its final metrics are unavailable and it is excluded from model selection. This is an observed optimization failure, not a zero score. Lower learning rates generally underfit within eight epochs. These measurements apply to the pinned 131-class snapshot, not external photographs.'))
nb.cells.insert(-2,nbformat.v4.new_code_cell("# Verify results independently from saved labels and predictions.\nimport subprocess\nsubprocess.run([sys.executable,str(ROOT/'scripts/verify_expanded_results.py')],cwd=ROOT,check=True)"))
NotebookClient(nb,timeout=180,kernel_name='prootypie-venv',resources={'metadata':{'path':str(r)}}).execute()
nbformat.write(nb,p)
outputs=sum(len(c.get('outputs',[]))for c in nb.cells if c.cell_type=='code')
assert outputs>0
assert not any(o.get('output_type')=='error'for c in nb.cells if c.cell_type=='code'for o in c.get('outputs',[]))
print({'cells':len(nb.cells),'outputs':outputs,'executed':True})
