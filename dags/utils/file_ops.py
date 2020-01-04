import filecmp
import json
import logging
import os
import shutil
from glob import glob

import requests


def get_parent_folder_name(dir_path):
    """
    Utility function to get lastest folder name from path
    :param dir_path: path
    :return: parent folder name
    """
    return os.path.split(os.path.dirname(dir_path))[1]


def get_files_in_directory(dir_path, file_ext):
    """
    Utility function to get all files from a given folder
    :param dir_path: path
    :param file_ext: file extension
    :return: a list of filepath
    """
    return glob(os.path.join(dir_path, file_ext))


def get_subfolders_in_directory(dir_path):
    """
    Utility function to get all first level subfolder paths from a given directory
    :param dir_path: A directory path
    :raises ValueError: Error raised when given path is not a folder
    :return: A list of subfolder paths
    """

    if os.path.isdir(dir_path):
        folder_paths = []
        for entry_name in os.listdir(dir_path):
            entry_path = os.path.join(dir_path, entry_name)
            if os.path.isdir(entry_path):
                folder_paths.append(entry_path)
        return folder_paths

    raise ValueError("The value of the dir_path argument must be a valid directory path")


def get_subfolders_names_in_directory(dir_path):
    """
    Utility function to get all the subfolders names

    :param dir_path: A directory path
    :raises ValueError: Error raised when given path is not a folder
    :return: A list of subfolder paths
    """
    if os.path.isdir(dir_path):
        folder_names = []
        for entry_name in os.listdir(dir_path):
            entry_path = os.path.join(dir_path, entry_name)
            if os.path.isdir(entry_path):
                folder_names.append(entry_name)
        return folder_names
    raise ValueError("The value of the dir_path argument must be a valid directory path")


def get_filename(file_path, with_extension=True):
    """
    A Utility function to get the filename with/without extension given a path
    :param file_path: A file path
    :param with_extension: Include extension into filename
    :return: Filename with or without extension
    """

    if with_extension:
        return os.path.basename(file_path)

    return os.path.splitext(os.path.basename(file_path))[0]


def get_folder_name(folder_path):
    """
    A Utility function to get the name of the latest folder in a path

    :param folder_path: Folder path
    :return: Folder name
    """
    return os.path.basename(folder_path)


def get_object_name_from_file(file_path):
    """
    get_object_name_from_file

    Get the object name from a file

    :param file_path: File path
    :return: Object name
    """
    filename = os.path.splitext(os.path.basename(file_path))[0]
    object_name = filename.split("_")[1]

    return object_name


def get_ontology_name_from_file(file_path):
    """
    get_ontology_name_from_file

    Get the ontology associated with this object

    :param file_path: File location
    :return: Ontology name
    """

    filename = os.path.splitext(os.path.basename(file_path))[0]
    anthology_name = filename.split("_")[0]

    return anthology_name


def get_source_feed_from_folder_name(dir_path):
    """
    get_source_feed_from_folder_name

    Get source feed from tf record name

    :param dir_path: TFRecord folder name
    :return: Source feed name
    """

    if os.path.isdir(dir_path):
        dir_name = os.path.basename(dir_path)
        source_feed = dir_name.split("_")[0]
        return source_feed

    raise ValueError(f"The specified path is not a directory: {dir_path}")


def get_filenames_in_directory(dir_path, file_ext):
    """
    A Utility function to get the filenames of files in a given folder
    with/without extension given a path
    :param dir_path: A directory path
    :param with_extension: Include extension into filename
    :return: Filename with or without extension
    """
    filepaths = get_files_in_directory(dir_path, file_ext)

    return [get_filename(f) for f in filepaths]


def get_sub_folders_list(dir_path):
    """
     Generate a list of subfolder from a folder path
    : param dir_path: folder path
    : return: list of sub folder path
    """
    return glob(os.path.join(dir_path, "*", ""))


def gcs_path_to_local_path(images_path, gcs_path):
    """
    Convert a Google Cloud Storage link into a local path to get an image
    : param image_path: Needed to find the images path within the container
    : param gcs_path: GCS Link to be converted
    : return: Converted local path to the image
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
            with open(f, "rb") as infile:
                data = json.load(infile)
                json_dict += data
        json.dump(json_dict, out)


def folder_exist_or_create(folder_path):
    # TODO: Add docstring
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def file_exist(file_path):
    # TODO: Add docstring
    return os.path.isfile(file_path)


def get_directory_subfolders_subset(dir_path, filter):
    # TODO: Add docstring
    subfolders = get_sub_folders_list(dir_path)

    parsed_subfolder = []
    for subfolder in subfolders:
        folder_name = os.path.basename(os.path.normpath(subfolder))

        if folder_name.startswith(filter):
            parsed_subfolder.append(subfolder)

    return parsed_subfolder


def copy_xml_files_from_folder(source_dir, dest_dir):
    # TODO: docs string
    files = glob(os.path.join(source_dir, "*.xml"))
    for file in files:
        if os.path.isfile(file):
            shutil.copy2(file, dest_dir)


def copy_files_from_folder(source_dir, dest_dir):
    # TODO: docs string
    files = glob(os.path.join(source_dir, "*.*"))
    for file in files:
        if os.path.isfile(file):
            shutil.copy2(file, dest_dir)
