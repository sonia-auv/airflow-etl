import os
import json
import logging

from utils import file_ops


def get_gcp_training_data_url(json_file, **kwargs):
    with open(json_file, "r") as infile:
        json_data = json.load(infile)
    try:
        gcp_url = json_data["gcp_url"]
        return gcp_url
        # ti = kwargs["ti"]
        # ti.xcom_push(key="gcp_training_data_url", value=gcp_url)
    except KeyError as e:
        logging.error(f"gcp_url key does not exist in json data. Validate file content {json_file}")
        raise e


