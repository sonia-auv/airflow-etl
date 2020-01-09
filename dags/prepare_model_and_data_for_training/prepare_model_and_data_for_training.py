import filecmp
import glob
import json
import logging
import os
import re
import shutil
import tarfile

import pandas as pd
import requests

import mistune
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
            model_name = model_name.replace("☆", "")
            model_name = model_name.strip()

            model_url = link.attrs["href"]
            model_file_name = model_url.split("/")[-1]
            model_folder_name = os.path.splitext(os.path.basename(model_file_name))[0]
            model_folder_name = os.path.splitext(os.path.basename(model_folder_name))[0]
            try:
                model_release_date = re.search(r"\d{4}_\d{2}_\d{2}", model_file_name).group()
            except:
                model_release_date = None

            data.append(
                (model_release_date, model_folder_name, model_file_name, model_url, model_name)
            )

    logging.info(f"Parsed all model data from the webpage {response.url}")

    return pd.DataFrame(
        data,
        columns=[
            "model_release_date",
            "model_folder_name",
            "model_file_name",
            "model_url",
            "model_name",
        ],
    )


def validate_reference_model_list_exist_or_create(
    base_model_csv, positive_downstream, negative_downstream
):
    if file_ops.file_exist(base_model_csv):
        return positive_downstream
    else:
        return negative_downstream


def download_reference_model_list_as_csv(url, base_model_csv):
    try:
        response = requests.get(url, allow_redirects=True)
        new_models_reference_df = __parse_downloaded_model_file_list_response(response)
        new_models_reference_df.to_csv(base_model_csv)
        logging.info("Model list data saved to csv file")
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while downloading the file from {url}")


def download_and_extract_base_model(base_model_csv, base_model_folder, required_base_models=None):

    models_df = pd.read_csv(base_model_csv)
    models_subset = models_df[["model_folder_name", "model_file_name", "model_url", "model_name"]]

    if required_base_models is not None:
        models_subset = models_subset[models_df.model_name.isin(required_base_models)]

    models = [tuple(x) for x in models_subset.values]
    subfolders = file_ops.get_subfolders_names_in_directory(base_model_folder)

    for model_folder_name, model_file_name, model_url, model_name in models:
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


def validate_requested_model_exist_in_model_zoo_list(base_models_csv, required_base_models):

    df = pd.read_csv(base_models_csv)
    available_models = df["model_name"].unique()

    if len(required_base_models) <= 0:
        raise ValueError(
            "Airflow variable training_required_base_models should contain at least one model to train"
        )

    for required_model in required_base_models:
        if required_model not in available_models:
            raise ValueError(
                "Required model {required_model} does not exist in the official tensorflow model zoo"
            )
    logging.info("All required model exist in the official tensorflow model zoo reference list")


def validate_model_presence_in_model_repo_or_create(model_repo_folder, video_source, base_model):

    model_folder = os.path.join(model_repo_folder, f"{video_source}_{base_model}")

    file_ops.folder_exist_or_create(model_folder)


def __create_training_folder_subtree(training_data_folder, **kwargs):

    # Base Folder
    data_folder = os.path.join(training_data_folder, "data")
    model_folder = os.path.join(training_data_folder, "model")
    # training_folder = os.path.join(training_data_folder, "training")

    images_folder = os.path.join(data_folder, "images")
    annotations_folder = os.path.join(data_folder, "annotations")
    xmls_folder = os.path.join(data_folder, "annotations", "xmls")
    tf_record_folder = os.path.join(data_folder, "tf_records")
    tf_record_train_folder = os.path.join(tf_record_folder, "train")
    tf_record_val_folder = os.path.join(tf_record_folder, "val")
    base_model_folder = os.path.join(model_folder, "base")
    # trained_model_folder = os.path.join(model_folder, "trained")

    # train_data_folder = os.path.join(training_folder, "training")
    # eval_data_folder = os.path.join(training_folder, "evaluation")

    training_folders = {
        "base_folder": training_data_folder,
        "data_folder": data_folder,
        "model_folder": model_folder,
        "images_folder": images_folder,
        "annotations_folder": annotations_folder,
        "xmls_folder": xmls_folder,
        "tf_record_folder": tf_record_folder,
        "tf_record_train_folder": tf_record_train_folder,
        "tf_record_val_folder": tf_record_val_folder,
        "base_model_folder": base_model_folder,
        # "trained_model_folder": trained_model_folder,
        # "train_data_folder": train_data_folder,
        # "eval_data_folder": eval_data_folder,
    }

    data_folders = [
        training_folders["images_folder"],
        training_folders["xmls_folder"],
        training_folders["tf_record_train_folder"],
        training_folders["tf_record_val_folder"],
        training_folders["base_model_folder"],
        # training_folders["trained_model_folder"],
        # training_folders["train_data_folder"],
        # training_folders["eval_data_folder"],
    ]

    for folder in data_folders:
        os.makedirs(folder)

    ti = kwargs["ti"]
    ti.xcom_push(key="training_folders", value=training_folders)
    logging.info("Training folder subtree has been created successfully")


def create_training_folder(
    base_training_folder, tf_record_folder, video_source, execution_date, base_model, **kwargs,
):
    subfolders = file_ops.get_directory_subfolders_subset(tf_record_folder, video_source)

    object_names_set = set()
    for subfolder in subfolders:
        folder_name = os.path.basename(os.path.normpath(subfolder))
        if folder_name.startswith(video_source):

            object_names = subfolder.split("_")[1]
            object_names_set.update(object_names.split("-"))

    object_names = "-".join(list(object_names_set))

    training_folder = os.path.join(
        base_training_folder, f"{video_source}_{object_names}_{base_model}_{execution_date}"
    )

    __create_training_folder_subtree(training_folder, **kwargs)

    ti = kwargs["ti"]
    ti.xcom_push(key="training_folder", value=training_folder)


def copy_labelbox_output_data_to_training_folder(
    labelbox_output_data_folder,
    tf_record_folder,
    video_source,
    base_model,
    airflow_base_folder,
    gcp_base_bucket_url,
    **kwargs,
):
    ti = kwargs["ti"]
    training_folders = ti.xcom_pull(
        key="training_folders", task_ids=f"create_training_folder_tree_{video_source}_{base_model}"
    )

    filtered_subfolders = file_ops.get_directory_subfolders_subset(
        labelbox_output_data_folder, video_source
    )

    for subfolder in filtered_subfolders:
        subfolders = file_ops.get_subfolders_in_directory(subfolder)

        subfolders = [
            image_subfolder for image_subfolder in subfolders if image_subfolder.endswith("images")
        ]

        images_folder = subfolders[0]

        file_ops.copy_files_from_folder(images_folder, training_folders["images_folder"])

        logging.info("Image files copy completed")

        file_ops.copy_xml_files_from_folder(subfolder, training_folders["xmls_folder"])

        logging.info("XML files copy completed")

    subfolders = file_ops.get_directory_subfolders_subset(tf_record_folder, video_source)

    labelmap_files = []
    trainval_files = []
    tf_record_files = []
    for subfolder in subfolders:
        labelmap_files.extend(glob.glob(subfolder + "/*.pbtxt"))
        trainval_files.extend(glob.glob(subfolder + "/*.txt"))
        tf_record_files.extend(glob.glob(subfolder + "/*.record"))

    labelmap_file = f"{training_folders['annotations_folder']}/labelmap.pbtxt"
    trainval_file = f"{training_folders['annotations_folder']}/trainval.txt"

    with open(labelmap_file, "w") as outfile:
        with open(labelmap_files[0]) as infile:
            for line in infile:
                outfile.write(line)

    with open(trainval_file, "w") as outfile:
        for trainval_file in trainval_files:
            with open(trainval_file, "r") as infile:
                shutil.copyfileobj(infile, outfile)

    for tf_record_file in tf_record_files:

        if (tf_record_file).endswith("train.record"):
            shutil.copy2(tf_record_file, training_folders["tf_record_train_folder"])
        else:
            shutil.copy2(tf_record_file, training_folders["tf_record_val_folder"])

    project_name = training_folders["base_folder"].replace(airflow_base_folder + "/training/", "")
    gcp_project_folder = f"{gcp_base_bucket_url}{project_name}/"

    gcp_training_files = {
        "label_map_file": labelmap_file.replace(
            airflow_base_folder + "/training/", gcp_base_bucket_url
        ),
        "train_tf_records": f"{gcp_project_folder}data/tf_record/train/*.record",
        "val_tf_records": f"{gcp_project_folder}data/tf_record/val/*.record",
    }

    ti = kwargs["ti"]
    ti.xcom_push(key="gcp_training_files", value=gcp_training_files)


def copy_base_model_to_training_folder(
    base_model_folder,
    base_model_csv,
    base_model,
    video_source,
    airflow_base_folder,
    gcp_base_bucket_url,
    **kwargs,
):
    ti = kwargs["ti"]
    training_folders = ti.xcom_pull(
        key="training_folders", task_ids=f"create_training_folder_tree_{video_source}_{base_model}"
    )

    gcp_training_files = ti.xcom_pull(
        key="gcp_training_files",
        task_ids=f"copy_labelbox_output_data_to_training_folder_{video_source}_{base_model}",
    )

    base_models_df = pd.read_csv(base_model_csv)

    model_df = base_models_df.loc[base_models_df["model_name"] == base_model]

    base_model_folder_name = model_df.iloc[0]["model_folder_name"]

    model_folder = os.path.join(base_model_folder, base_model_folder_name)

    file_ops.copy_files_from_folder(model_folder, training_folders["base_model_folder"])

    logging.info("Successfully copied all base model file to training folder")

    pipeline_file = os.path.join(training_folders["base_model_folder"], "pipeline.config")

    os.remove(pipeline_file)

    model_checkpoint = os.path.join(training_folders["base_model_folder"], "model.ckpt")

    logging.info("Successfully removed pipeline.config file")

    gcp_training_files["model_checkpoint"] = model_checkpoint.replace(
        airflow_base_folder + "/training/", gcp_base_bucket_url
    )

    ti = kwargs["ti"]
    ti.xcom_push(key="gcp_training_files", value=gcp_training_files)


def generate_model_config(
    video_source, base_model, model_config_template, num_classes, **kwargs,
):

    ti = kwargs["ti"]
    training_folders = ti.xcom_pull(
        key="training_folders", task_ids=f"create_training_folder_tree_{video_source}_{base_model}"
    )
    gcp_training_files = ti.xcom_pull(
        key="gcp_training_files",
        task_ids=f"copy_base_model_to_training_folder_{video_source}_{base_model}",
    )

    # Replacing placeholders in airflow variables for values
    model_config_template = re.sub("NUM_CLASSES", str(num_classes), model_config_template)
    model_config_template = re.sub(
        "PRE_TRAINED_MODEL_CHECKPOINT_PATH",
        gcp_training_files["model_checkpoint"],
        model_config_template,
    )
    model_config_template = re.sub(
        "LABEL_MAP_PATH", gcp_training_files["label_map_file"], model_config_template
    )
    model_config_template = re.sub(
        "TRAIN_TF_RECORD_PATH", str(gcp_training_files["train_tf_records"]), model_config_template
    )
    model_config_template = re.sub(
        "VAL_TF_RECORD_PATH", str(gcp_training_files["val_tf_records"]), model_config_template
    )

    try:
        config_file = os.path.join(training_folders["base_folder"], "pipeline.config")
        with open(config_file, "w") as outfile:
            outfile.write(model_config_template)
        logging.info("Model config file has been created succesfully")
    except IOError as e:
        logging.error(
            "An error has been raised while trying to save the model config to a file on disk"
        )
        raise e


def archiving_training_folder(training_archiving_path, video_source, base_model, **kwargs):
    ti = kwargs["ti"]
    training_folders = ti.xcom_pull(
        key="training_folders", task_ids=f"create_training_folder_tree_{video_source}_{base_model}"
    )
    print(training_archiving_path)
    print(training_folders)
    folder_name = file_ops.get_folder_name(training_folders["base_folder"])
    archive_file = os.path.join(training_archiving_path, f"{folder_name}.tar")

    with tarfile.open(archive_file, "w:gz") as tar:
        tar.add(training_folders["base_folder"], arcname=folder_name)

    logging.info(
        f"Successfully created archive of training folder : {training_folders['base_folder']}"
    )


def remove_raw_images_and_annotations_from_training_folder(
    video_source, base_model, gcp_base_bucket_url, airflow_trainable_folder, **kwargs
):
    ti = kwargs["ti"]
    training_folders = ti.xcom_pull(
        key="training_folders", task_ids=f"create_training_folder_tree_{video_source}_{base_model}"
    )
    shutil.rmtree(training_folders["xmls_folder"])
    shutil.rmtree(training_folders["images_folder"])
    os.remove(os.path.join(training_folders["annotations_folder"], "trainval.txt"))

    training_folder = training_folders["base_folder"]

    prepared_cmd = f"gsutil -m cp -r {training_folder} {gcp_base_bucket_url}"

    training_folder_name = file_ops.get_folder_name(training_folder)

    json_data = {}
    json_data["gcp_url"] = f"{gcp_base_bucket_url}{training_folder_name}"

    json_file = os.path.join(airflow_trainable_folder, f"{training_folder_name}.json")
    with open(json_file, "w") as outfile:
        json.dump(json_data, outfile, indent=4)

    ti.xcom_push(key="gcp_copy_cmd", value=prepared_cmd)

    logging.info("Successfully deleted useless files for training")


def clean_up_post_training_prep(folders, **kwargs):

    print(folders)
    for folder in folders:
        folder_content = glob.glob(f"{folder}/*")
        print(folder_content)

        for content in folder_content:
            if os.path.isdir(content):
                logging.info(f"Deleting Folder:{content}")
                shutil.rmtree(content)
            else:
                if not content.endswith(".gitignore"):
                    logging.info(f"Deleting File:{content}")
                    os.remove(content)
