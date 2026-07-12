const fs = require('fs');
const content = fs.readFileSync('src/PatientChat.tsx', 'utf-8');

let tags = [];
let lineNo = 1;
const lines = content.split('\n');

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  // naive tag counter for this specific file formatting
  const openMatches = line.match(/<div[ >]/g);
  const closeMatches = line.match(/<\/div>/g);
  
  // self closing matches
  const selfClosingMatches = line.match(/<div[^>]*\/>/g);
  
  const opens = (openMatches ? openMatches.length : 0) - (selfClosingMatches ? selfClosingMatches.length : 0);
  const closes = closeMatches ? closeMatches.length : 0;
  
  for(let j = 0; j < opens; j++) tags.push({line: i + 1, type: 'div'});
  for(let j = 0; j < closes; j++) {
    if (tags.length > 0) tags.pop();
  }
}
console.log('Remaining open divs:', tags);
