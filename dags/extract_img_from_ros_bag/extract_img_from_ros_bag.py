import logging
import os
import glob


def bag_file_exists(bag_path):
    """
    Check if the bag file are present
    :param bag_path: Location of the folder containing ROS bag
    """
    files = glob.glob(os.path.join(bag_path, '*.bag'))

    if files:
        for bag in files:
            logging.info("Bag found at {}".format(bag))
        return True

    logging.info("Bag file not detected in {}".format(bag_path))
    return False
