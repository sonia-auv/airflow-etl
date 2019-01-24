import logging
import os
import uuid
from glob import glob
import cv2
import rosbag
from cv_bridge import CvBridge


def generate_uuid1_name():
    """
    Generate a unique identifier for each generated images.
    :return: uuid 1 identifier
    """
    uuid_name = str(uuid.uuid1())

    uuid_formated_name = "frame_{}.jpg".format(uuid_name)

    return uuid_formated_name


def generate_output_dir_path(sub_folder, output_dir):

    object_name = os.path.split(os.path.dirname(sub_folder))[1]
    new_output_dir = os.path.join(output_dir, object_name)

    logging.info("New output dir : {}".format(new_output_dir))

    return new_output_dir


def dir_contains_bag_file(bag_folder):
    """
     Validate a given directory does contain an file with a given extension.
    :param dir_path: folder path
    :param extension:  wanted file extension
    :return: file with given extension found or not status
    """
    files = glob(os.path.join(bag_folder, "*", "*.bag"))
    logging.info(files)

    if len(files) > 0:
        logging.info("New bag file detected in folder")
        return "task_extract_image"
    else:
        logging.info("New bag file not detected in folder")
        return "task_notify_file_with_ext_failure"


def extract_images_from_bag(bag_folder, topics, output_dir):

    bridge = CvBridge()

    sub_folders = glob(os.path.join(bag_folder, "*", ""))

    logging.info("Sub folders found : {}".format(sub_folders))

    for sub_folder in sub_folders:

        logging.info("Processing sub folder {}".format(sub_folder))

        img_output_dir = generate_output_dir_path(sub_folder, output_dir)

        if not os.path.exists(img_output_dir):
            os.makedirs(img_output_dir)
            logging.info("Output image directory created at{}".format(img_output_dir))

        bag_files = glob(os.path.join(sub_folder, "*.bag"))

        logging.info("Bag founds:{}".format(bag_files))

        for bag_file in bag_files:
            for topic in topics:
                logging.info("Extracting images from {} on topic {}".format(bag_file, topics))

                with rosbag.Bag(bag_file, "r") as bag:
                    for topic, msg, _ in bag.read_messages(topics=[topic]):

                        img_name = generate_uuid1_name()
                        extraction_path = os.path.join(img_output_dir, img_name)

                        cv_img = bridge.compressed_imgmsg_to_cv2(
                            msg, desired_encoding="passthrough"
                        )
                        cv2.imwrite(extraction_path, cv_img)
                        logging.info("Extracted image {} to {}".format(img_name, extraction_path))

        logging.info("Extraction of all bags complete with success")
