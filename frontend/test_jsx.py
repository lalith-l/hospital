import re

with open('src/PatientChat.tsx') as f:
    text = f.read()
idx = text.find('  return (')
text = text[idx:]
text = re.sub(r'\{\s*/\*.*?\*/\s*\}', '', text, flags=re.DOTALL)

def check_tags(text):
    tags = re.findall(r'<(div|span|button|p|h2|h3|h4|svg|g|path|circle|line)(?: [^>]*)?(/?)>', text)
    closes = re.findall(r'</(div|span|button|p|h2|h3|h4|svg|g|path|circle|line)>', text)
    
    open_counts = {}
    for t, is_self_closing in tags:
        if not is_self_closing:
            open_counts[t] = open_counts.get(t, 0) + 1
    
    close_counts = {}
    for t in closes:
        close_counts[t] = close_counts.get(t, 0) + 1
        
    for t in open_counts:
        print(f"{t}: {open_counts[t]} opens, {close_counts.get(t, 0)} closes")

check_tags(text)
