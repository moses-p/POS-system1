import os

search_root = r'C:/Users'
found = []

for dirpath, dirnames, filenames in os.walk(search_root):
    for filename in filenames:
        if filename == 'pos.db':
            found.append(os.path.join(dirpath, filename))

if len(found) == 1:
    print(f"SUCCESS: Only one pos.db remains: {found[0]}")
elif len(found) == 0:
    print("WARNING: No pos.db files found!")
else:
    print("WARNING: Multiple pos.db files found:")
    for f in found:
        print(f"  - {f}") 