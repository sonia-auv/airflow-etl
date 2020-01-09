import logging
import os
import glob
from datetime import datetime


def bag_file_exists(bag_path):
    """
    Check if the bag file are present
    :param bag_path: Location of the folder containing ROS bag
    """
    files = glob.glob(os.path.join(bag_path, "*.bag"))

    if files:
        for bag in files:
            logging.info("Bag found at {}".format(bag))
        return True

    logging.info("Bag file not detected in {}".format(bag_path))
    return False


def bag_filename_syntax_valid(bag_path):
    """
    Validate bag filename syntax
    :param bag_path: Location of the folder containing ROS bag
    """
    files = glob.glob(os.path.join(bag_path, "*.bag"))

    if files:
        for bag in files:
            filename = os.path.basename(bag)
            filename_wo_extension = os.path.splitext(filename)[0]

            # TODO: Handle error here
            splited_filename = filename_wo_extension.split("_")

            source_name = splited_filename[0]
            object_name = splited_filename[1]
            location_name = splited_filename[2]
            filename_date = splited_filename[3]

            if not all(isinstance(item, str) for item in splited_filename):
                logging.info(
                    "[ERROR]: Bag filename must respect the following syntax object_location_date i.e: dice_cvm_fron__20190909"
                )
                return False
            try:
                date = datetime.strptime(date, "%Y%m%d")
            except:
                logging.info(
                    "[ERROR]: Bag filename must respect the following syntax object_location_date i.e: dice_cvm_20190909"
                )
                return False

    return True
