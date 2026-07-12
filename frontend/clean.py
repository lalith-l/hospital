with open('src/PatientChat.tsx', 'r') as f:
    text = f.read()

import re
text = re.sub(r'const audioChunksRef = useRef<Blob\[\]>\(\[\]\);', '// const audioChunksRef = useRef<Blob[]>([]);', text)
text = re.sub(r'const \{ transcript, listening, browserSupportsSpeechRecognition \} = useSpeechRecognition\(\);', 'const { transcript, listening } = useSpeechRecognition();', text)

with open('src/PatientChat.tsx', 'w') as f:
    f.write(text)
