import sys

with open('PatientChat.tsx', 'r') as f:
    orig = f.read()
    
with open('new_return.tsx', 'r') as f:
    new_ret = f.read()

# Find the last "return (" inside the main component block
# To be safe, we can find the index of "  return (" and we know it's at the end
start_idx = orig.rfind("  return (")
if start_idx == -1:
    print("Could not find return statement!")
    sys.exit(1)

# we just slice and replace
final = orig[:start_idx] + new_ret + "\n}\n\nexport default PatientChat;\n"

with open('PatientChat.tsx', 'w') as f:
    f.write(final)

print("Successfully replaced return block")
