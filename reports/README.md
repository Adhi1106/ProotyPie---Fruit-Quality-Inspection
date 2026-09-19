# Illustrated submission report

Use ProotyPie_Project_Report.pdf for submission (12 A4 pages). The DOCX is editable. Both include actual production-build browser screenshots, all 12 validation configurations, learning curves, test confusion matrix, methodology, architecture and limitations.

The older Markdown report is background text only; the illustrated PDF/DOCX supersede it. Screenshot evidence and JSON exports are in screenshots/. Rebuild with python reports/build_premium_report.py (requires python-docx, reportlab and Pillow).

Browser verification: start API on port 8000 and frontend production build on port 3027; install Playwright and Chromium, then run frontend/tests/capture-results.cjs.
