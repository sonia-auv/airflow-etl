import os
import logging
import csv
import json

from utils import file_ops


def create_csv(images_path, gcs_images_path, dataset, csv_path):
    # Create array of image urls in GCS
    file_names = os.listdir(os.path.join(images_path, dataset))
    urls = list(map(lambda x: os.path.join(gcs_images_path, x), file_names))

    # Export CSV
    csv_file_path = os.path.join(csv_path, dataset)
    with open(csv_file_path + ".csv", "wb") as csv_file:
        writer = csv.writer(csv_file, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Image_URL"])
        map(lambda x: writer.writerow([x]), urls)


def create_json(images_path, gcs_images_path, json_path):
    #  """
    #  Utility function generate a json file containing the urls to image file
    #  stored in google cloud bucket to import projet into labelbox
    # :param images_path
    # :param gcs_images_path
    # :param json_path
    # :return:
    # """
    sub_folders = file_ops.get_sub_folders_list(images_path)

    data = []

    for folder in sub_folders:
        print(folder)
        filenames = file_ops.get_filenames_in_directory(folder, "*.jpg")
        print(filenames)
        for filename in filenames:
            gcp_url = os.path.join(
                gcs_images_path, file_ops.get_parent_folder_name(folder), filename
            )
            json_data = {"imageUrl": gcp_url}
            data.append(json_data)

        json_file = json_path + "/" + file_ops.get_parent_folder_name(folder) + ".json"

        with open(json_file, "w") as f:
            json.dump(data, f)
