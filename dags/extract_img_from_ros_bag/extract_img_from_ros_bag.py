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

def bag_file_exists(bags_path, dataset):
    """
    Check if the bag file exists
    :param bag_path: Location of the bag path
    """
    bag_path = os.path.join(bags_path, dataset) + ".bag"
    if os.path.exists(bag_path):
        logging.info("Bag found at {}".format(bag_path))
        return "task_extract_images_from_bag"
    else:
        return "task_bag_not_detected"


def bag_not_detected(bags_path, dataset):
    bag_path = os.path.join(bags_path, dataset) + ".bag"
    return "Bag file {} not detected".format(bag_path)

def extract_images_from_bag(bags_path, images_path, dataset, topics):
    # Create output dir if it doesn't exist
    image_output_dir = os.path.join(images_path, dataset)
    if not os.path.exists(image_output_dir):
        os.makedirs(image_output_dir)

    # Extract images from bag
    bag_file = os.path.join(bags_path, dataset) + ".bag"
    bridge = CvBridge()

    for topic in topics:
        with rosbag.Bag(bag_file, "r") as bag:
            logging.info("Extracting images from {} on topic {}".format(bag_file, topic))
            for topic, msg, _ in bag.read_messages(topics=[topic]):

                img_name = generate_uuid1_name()
                extraction_path = os.path.join(image_output_dir, img_name)

                cv_img = bridge.compressed_imgmsg_to_cv2(
                    msg, desired_encoding="passthrough"
                )
                cv2.imwrite(extraction_path, cv_img)
                logging.info("Extracted image {} to {}".format(img_name, extraction_path))