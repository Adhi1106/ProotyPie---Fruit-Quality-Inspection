from docx import Document
from docx.shared import Pt
from pathlib import Path

path = Path('/home/hermes/workspace/projects/prootypie/reports/ProotyPie_Project_Report.docx')
doc = Document(path)
for style_name in ['List Bullet', 'List Number', 'Normal']:
    try:
        doc.styles[style_name].font.name = 'Arial'
        doc.styles[style_name].font.size = Pt(10.5)
    except Exception:
        pass
doc.save(path)
print('updated styles')
