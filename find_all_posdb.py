import os

search_root = r'C:/Users'
 
for dirpath, dirnames, filenames in os.walk(search_root):
    for filename in filenames:
        if filename == 'pos.db':
            print(os.path.join(dirpath, filename)) 