import os, os.path, random
mypath = "images/phone_plus_2022-07-29-11-06-29"
percentage_to_remove = 12.0 / 112.0

for root, dirs, files in os.walk(mypath):
    for file in files:
        if random.random() <= percentage_to_remove:
            os.remove(os.path.join(root, file))
