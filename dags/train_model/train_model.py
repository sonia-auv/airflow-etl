import os
import filecmp
import logging

from utils import file_ops


def get_tf_record_folders(source_camera, tfrecord_dir):
    subfolders = file_ops.get_sub_folders_list(tfrecord_dir)

    tf_record_folders = []
    for subfolder in subfolders:
        source_feed = file_ops.get_source_feed_from_folder_name()
        if source_feed == source_camera:
            tf_record_folders.append(subfolder)

    return tf_record_folders


def compare_label_map_file(tf_records_folders):

    label_maps = []
    for path, subdirs, files in os.walk(tf_records_folders):
        for file_name in files:
            if file_name.endswith(".pbtxt"):
                label_maps.append(os.path.join(path, file_name))

    reference_label_map = label_maps[0]
    labelmap_match = True
    print("--------- Labelmap Compare ----------")
    print(f"Reference Map :{reference_label_map}")
    for label_map in label_maps:
        if filecmp(label_map, reference_label_map):
            print(f"[ MATCH ] | LabelMap:{label_map} ")
        else:
            print(f"[ FAILED ] | LabelMap:{label_map} ")
            labelmap_match = False

    if labelmap_match == False:
        raise ValueError("Comparing labelmap file failed")
