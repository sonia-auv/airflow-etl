import os
import logging

def generate_trainval_file(annotation_dir, output_file):
    files = []
    with open(output_file, 'w') as fd:
        for r, d, f in os.walk(annotation_dir):
            for file in f:
                line = file.split(".")[0]
                fd.write(line + '\n')