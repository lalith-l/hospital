with open('src/PatientChat.tsx') as f:
    text = f.read()

import re
# remove string literals
text = re.sub(r'".*?(?<!\\)"', '""', text)
text = re.sub(r"'.*?(?<!\\)'", "''", text)
text = re.sub(r'`[^`]*`', '``', text)
# remove jsx tags to some extent? no, braces inside jsx evaluate JS
# let's just count { and } and print lines where they don't match
stack = []
for i, char in enumerate(text):
    if char == '{':
        stack.append(i)
    elif char == '}':
        if stack:
            stack.pop()
        else:
            print(f"Extra }} at pos {i}")

if stack:
    for pos in stack:
        # line number
        line = text[:pos].count('\n') + 1
        print(f"Unclosed {{ at line {line}")
