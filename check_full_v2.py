import ast
import sys
from collections import Counter

src = open('frontend/app.py', encoding='utf-8').read()

# Syntax check
tree = ast.parse(src)
print('SYNTAX OK')

# Function duplicate check
funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
counts = Counter(funcs)
dups = [k for k, v in counts.items() if v > 1]
if dups:
    print('DUPLICATE FUNCTIONS:', dups)
    sys.exit(1)
else:
    print('No duplicate functions.')

# Banned symbol check
banned = ['_esc_js', '_build_chat_html', '_CHAT_CSS', '_CHAT_CSS_SIDEBAR']
found = [b for b in banned if b in src]
if found:
    print('BANNED SYMBOLS FOUND:', found)
    sys.exit(1)
else:
    print('No banned symbols found.')

# Count def main() and def render_chat_assistant()
main_count = src.count('def main()')
chat_count = src.count('def render_chat_assistant()')
print(f'def main() occurrences: {main_count}')
print(f'def render_chat_assistant() occurrences: {chat_count}')
if main_count != 1 or chat_count != 1:
    print('ERROR: Expected exactly 1 of each!')
    sys.exit(1)

print('ALL CHECKS PASSED')
