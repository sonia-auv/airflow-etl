import os
import re
import glob
import shutil
import filecmp
import requests
import json
import mistune
import logging
import pandas as pd

from bs4 import BeautifulSoup
from utils import file_ops

logging.getLogger().setLevel(logging.INFO)


def __parse_downloaded_model_file_list_response(response):
    html = mistune.markdown(response.text)
    soup = BeautifulSoup(html)
    link_nodes = soup.find_all("a")

    data = []
    for link in link_nodes:
        if "http://download.tensorflow.org/models/object_detection/" in link.attrs["href"]:
            model_name = link.text
            model_url = link.attrs["href"]
            model_file_name = model_url.split("/")[-1]
            model_folder_name = os.path.splitext(os.path.basename(model_file_name))[0]
            model_folder_name = os.path.splitext(os.path.basename(model_folder_name))[0]
            try:
                model_release_date = re.search(r"\d{4}_\d{2}_\d{2}", model_file_name).group()
            except:
                model_release_date = None

            data.append((model_release_date, model_folder_name, model_file_name, model_url))

    return pd.DataFrame(
        data, columns=["model_release_date", "model_folder_name", "model_file_name", "model_url"]
    )


def reference_model_list_exist_or_create(base_model_csv, positive_downstream, negative_downstream):
    if file_ops.file_exist(base_model_csv):
        return positive_downstream
    else:
        return negative_downstream


def check_reference_model_list_different(url, base_model_csv):
    try:
        response = requests.get(url, allow_redirects=True)
        new_models_reference_df = __parse_downloaded_model_file_list_response(response)
        saved_models_reference_df = pd.read_csv(base_model_csv)

        if not new_models_reference_df.equals(saved_models_reference_df):
            new_models_reference_df.to_csv(base_model_csv)
        # return True
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while downloading the file from {url}")


def download_reference_model_list_as_csv(url, base_model_csv):
    try:
        response = requests.get(url, allow_redirects=True)
        new_models_reference_df = __parse_downloaded_model_file_list_response(response)
        new_models_reference_df.to_csv(base_model_csv)
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while downloading the file from {url}")


def download_and_extract_base_model(base_model_csv, base_model_folder, base_model_list=None):

    # TODO: Ease up model name handeling
    models_df = pd.read_csv(base_model_csv)

    models_subset = models_df[["model_folder_name", "model_file_name", "model_url"]]

    if base_model_list is not None:
        models_subset = models_subset[models_df.model_folder_name.isin(base_model_list)]

    models = [tuple(x) for x in models_subset.values]
    subfolders = file_ops.get_subfolders_names_in_directory(base_model_folder)

    for model_folder_name, model_file_name, model_url in models:
        if not model_folder_name in subfolders:
            logging.info(f"Model {model_folder_name} not found ")
            os.mkdir(os.path.join(base_model_folder, model_folder_name))
            try:
                response = requests.get(model_url, stream=True)
                logging.info(f"Downloading {model_url} .....")
                if response.status_code == 200:
                    tar_file = os.path.join(base_model_folder, model_file_name)
                    with open(tar_file, "wb") as f:
                        f.write(response.raw.read())

                    logging.info(f"Extracting {tar_file} .....")
                    shutil.unpack_archive(tar_file, os.path.join(base_model_folder))
                    os.remove(tar_file)
            except requests.exceptions.RequestException as e:
                logging.error(f"An error occurred while downloading the file from {model_url}")
        else:
            logging.info("All base models are already present")


def compare_label_map_file(base_tf_record_folder, video_source):

    subfolders = file_ops.get_directory_subfolders_subset(base_tf_record_folder, video_source)

    if len(subfolders) > 1:
        label_maps = []
        for subfolder in subfolders:
            label_maps.append(glob.glob(subfolder + "*.pbtxt")[0])
        reference_label_map = label_maps[0]
        labelmap_match = True
        for label_map in label_maps:
            print(label_map)
            logging.info(f"Reference File: {reference_label_map}")
            if filecmp.cmp(label_map, reference_label_map):
                print(f"[ MATCH ] | LabelMap:{label_map} ")
            else:
                print(f"[ FAILED ] | LabelMap:{label_map} ")
                labelmap_match = False

        return labelmap_match
    else:
        logging.warn(f"There were not enough dataset to compare i.g : Less than two")


def __create_training_folder_subtree(
    training_data_folder, video_source, object_names, execution_date
):

    # Base Folder

    input_data_folder = os.path.join(training_data_folder, "input_data")
    output_data_folder = os.path.join(training_data_folder, "output_data")

    # Input Data
    input_images_folder = os.path.join(input_data_folder, "images")
    input_annotations_folder = os.path.join(input_data_folder, "annotations", "xmls")
    input_tf_record_folder = os.path.join(input_data_folder, "tf_record")

    # Output Data
    output_checkpoint_folder = os.path.join(output_data_folder, "checkpoints")
    output_tensorboard_data_folder = os.path.join(output_data_folder, "tensorboard")
    output_tensorboard_training_folder = os.path.join(output_tensorboard_data_folder, "training")
    output_tensorboard_evaluation_folder = os.path.join(
        output_tensorboard_data_folder, "evaluation"
    )

    data_folders = [
        input_images_folder,
        input_annotations_folder,
        input_tf_record_folder,
        output_checkpoint_folder,
        output_tensorboard_training_folder,
        output_tensorboard_evaluation_folder,
    ]

    for folder in data_folders:
        os.makedirs(folder)

    logging.info("Training folder subtree has been created successfully")


def create_training_folder(
    training_data_folder, tf_record_folder, video_source, execution_date, **kwargs
):
    subfolders = file_ops.get_directory_subfolders_subset(tf_record_folder, video_source)

    # Parse
    json_data = {"datasets": [], "objects": []}
    object_names_set = set()
    for subfolder in subfolders:
        folder_name = os.path.basename(os.path.normpath(subfolder))
        if folder_name.startswith(video_source):

            json_data["datasets"].append(folder_name)
            object_names = subfolder.split("_")[1]
            object_names_set.update(object_names.split("-"))

    json_data["objects"] = list(object_names_set)
    object_names = "-".join(json_data["objects"])

    training_data_folder = os.path.join(
        training_data_folder, f"{video_source}_{object_names}_{execution_date}"
    )

    __create_training_folder_subtree(
        training_data_folder, video_source, object_names, execution_date
    )

    training_data_json_file = training_data_folder + "/datasets.json"
    with open(training_data_json_file, "w") as outfile:
        json.dump(
            json_data, outfile, indent=4,
        )

    ti = kwargs["ti"]
    ti.xcom_push(key="training_data_folder", value=training_data_folder)


def copy_labelbox_output_data_to_training(
    labelbox_output_data_folder, tf_record_folder, video_source, **kwargs
):
    ti = kwargs["ti"]

    training_data_folder = ti.xcom_pull(
        key="training_data_folder", task_ids=f"create_training_folder_tree_{video_source}"
    )

    # Training folder paths
    training_data_images_folder = os.path.join(training_data_folder, "input_data", "images")
    training_data_annotations_directory = os.path.join(
        training_data_folder, "input_data", "annotations"
    )
    training_data_xmls_directory = os.path.join(training_data_annotations_directory, "xmls")

    training_data_tfrecord_directory = os.path.join(training_data_folder, "input_data", "tf_record")

    filtered_subfolders = file_ops.get_directory_subfolders_subset(
        labelbox_output_data_folder, video_source
    )

    for subfolder in filtered_subfolders:
        subfolders = file_ops.get_subfolders_in_directory(subfolder)

        subfolders = [
            image_subfolder for image_subfolder in subfolders if image_subfolder.endswith("images")
        ]

        images_folder = subfolders[0]

        file_ops.copy_files_from_folder(images_folder, training_data_images_folder)

        logging.info("Image files copy completed")

        file_ops.copy_xml_files_from_folder(subfolder, training_data_xmls_directory)

        logging.info("XML files copy completed")

    subfolders = file_ops.get_directory_subfolders_subset(tf_record_folder, video_source)

    labelmap_files = []
    trainval_files = []
    tf_record_files = []
    for subfolder in subfolders:
        labelmap_files.extend(glob.glob(subfolder + "/*.pbtxt"))
        trainval_files.extend(glob.glob(subfolder + "/*.txt"))
        tf_record_files.extend(glob.glob(subfolder + "/*.record"))

    # shutil.copy2(labelmap_files[0], training_data_annotations_directory)

    with open(f"{training_data_annotations_directory}/labelmap.pbtxt", "w") as outfile:
        with open(labelmap_files[0]) as infile:
            for line in infile:
                outfile.write(line)

    with open(f"{training_data_annotations_directory}/trainval.txt", "wb") as outfile:
        for trainval_file in trainval_files:
            with open(trainval_file, "rb") as infile:
                shutil.copyfileobj(infile, outfile)

    for tf_record_file in tf_record_files:
        shutil.copy2(tf_record_file, training_data_tfrecord_directory)

    # TODO: Genereate one folder per model
    # TODO: Add templated model config file
    # TODO: Edit value in templated model config file
    # TODO: Create archive of training folder
    # TODO: Delete all annotations, images, and upload training training folder to GCP
