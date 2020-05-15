import fileinput
import json
import os
import re
import sys

def replace(file, pattern, subst):
    # https://stackoverflow.com/a/13641746
    # Read contents from file as a single string
    file_handle = open(file, 'r')
    file_string = file_handle.read()
    file_handle.close()

    # Use RE package to allow for replacement (also allowing for (multiline) REGEX)
    file_string = (re.sub(pattern, subst, file_string))

    # Write contents to file.
    # Using mode 'w' truncates the file.
    file_handle = open(file, 'w')
    file_handle.write(file_string)
    file_handle.close()

with open('substitutions.json','rb') as a:
    subs = json.load(a)

print(subs.keys())
print(subs.values())

if sys.argv[1] == 'add':
    val_from = subs.keys()
elif sys.argv[1] == 'remove':
    val_from = subs.values()
    val_to = subs.keys()
    subs = dict(zip(val_from,val_to))
else:
    print('Tell me what to do')
    val_from=[]

if not os.path.isdir(sys.argv[2]):
    print('not a dir')
else:
    folder = sys.argv[2]
    for eachfile in os.listdir(folder):
        if any(validext in eachfile for validext in ['.json','.py']):
            to_mod = os.path.join(folder,eachfile)
            print('Modifying', to_mod)
            for entry in val_from:
                replace(to_mod, str(entry),str(subs[entry]))

