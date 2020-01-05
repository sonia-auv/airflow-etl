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
