import ast
src = open('frontend/app.py', encoding='utf-8').read()
ast.parse(src)
print('SYNTAX OK')
