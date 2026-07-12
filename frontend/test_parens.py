with open('src/PatientChat.tsx') as f:
    text = f.read()

import re
# remove strings and template literals for safety
text = re.sub(r'".*?(?<!\\)"', '""', text)
text = re.sub(r"'.*?(?<!\\)'", "''", text)
text = re.sub(r'`[^`]*`', '``', text)

stack = []
for i, char in enumerate(text):
    if char == '(':
        stack.append(i)
    elif char == ')':
        if stack:
            stack.pop()

if stack:
    for pos in stack:
        line = text[:pos].count('\n') + 1
        print(f"Unclosed ( at line {line}")
