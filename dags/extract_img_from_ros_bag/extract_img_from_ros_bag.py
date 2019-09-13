import logging
import os
import glob


def bag_file_exists(bag_path):
    """
    Check if the bag file exists
    :param bag_path: Location of the bag path
    """
    files = glob.glob(os.path.join(bag_path, '*.bag'))

    if files:
        for bag in files:
            logging.info("Bag found at {}".format(bag))
        return "task_extract_images_from_bag"
    else:
        return "task_bag_not_detected"


def bag_not_detected(bag_path):
    return "Bag file not detected in {}".format(bag_path)
