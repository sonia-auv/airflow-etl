import csv
import os
import re
import shutil
import filecmp
import requests
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
        new_models_reference_df = __parse_downloaded_model_file_list_response(url)
        saved_models_reference_df = pd.load_csv(model_list_csv)

        if not new_models_reference_df.equals(saved_models_reference_df):
            new_models_reference_df.to_csv(model_list_csv)
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

    models_df = pd.read_csv(base_model_csv)

    models_subset = models_df[["model_folder_name", "model_file_name", "model_url"]]

    if base_model_list is not None:
        models_subset = models_subset[models_df.model_folder_name.isin(base_model_list)]

    models = [tuple(x) for x in models_subset.values]
    subfolders = file_ops.get_sub_folders_list(base_model_folder)

    for model_folder_name, model_file_name, model_url in models:
        if not model_folder_name in subfolders:
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


def prepare_training_input_data(
    training_input_folder, model_folder_name, target_cam, base_model_folder
):

    today = datetime.today().strftime("%Y_%m_%d")
    training_input_folder_name = f"{model_folder_name}_{target_cam}_{today}"
    training_input_folder = os.path.join(training_input_folder, training_input_folder_name)
    os.mkdir(training_input_folder)

    # TODO: Check if model folder exist
    # TODO: Copy model from base folder
    # TODO: Copy all data for target cam
    # TODO: Compare all labelmap.pbtxt
    # TODO: Join all trainval content
    # TODO: Copy all train.record and val.record
    # TODO: Edit model config file
    # TODO: compress content
    # TODO: Export to GCP
