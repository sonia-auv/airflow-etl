import os
import logging
from glob import glob
import json


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

def gcs_path_to_local_path(images_path, gcs_path):
     """
     Convert a Google Cloud Storage link into a local path to get an image
     :param image_path: Needed to find the images path within the container
     :param gcs_path: GCS Link to be converted
     :return: Converted local path to the image
     """
     split = gcs_path.split("/")

     dataset = split[3]
     image = split[4]

     return os.path.join(images_path, dataset, image)

def concat_json(json_files, output_path):
     """
     concat multiples json into one
    :param json_files: dictionnary of json file
    :param output_path: file name of the resulting json file
    :return: none
    """

     json_dict = []
     with open(output_path, "w") as out:
          for f in json_files:
               with open(f, 'rb') as infile:
                    data = json.load(infile)
                    json_dict += data
          json.dump(json_dict, out)