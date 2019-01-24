import os
import logging
from glob import glob


def get_parent_folder_name(dir_path):
    """
     Utility function to get lastest folder name from path
    :param dir_path: path
    :return: parent folder name
    """
    return os.path.split(os.path.dirname(dir_path))[1]


def get_sub_folders_list(dir_path):
    """
     Generate a list of subfolder from a folder path
    :param dir_path: folder path
    :return: list of sub folder path
    """
    return glob(os.path.join(dir_path), '*', '')



