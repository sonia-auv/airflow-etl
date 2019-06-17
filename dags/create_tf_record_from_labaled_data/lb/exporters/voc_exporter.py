"""
Module for converting labelbox.com JSON exports to Pascal VOC 2012 format.
"""

import json
import logging
import os
from typing import Any, Dict
import io

from PIL import Image
import requests
from shapely import wkt
import cv2
import numpy as np

from lb.exceptions import UnknownFormatError
from lb.exporters.pascal_voc_writer import Writer as PascalWriter


LOGGER = logging.getLogger(__name__)


def from_json(images_input_dir, labeled_data, annotations_output_dir, images_output_dir,
              label_format='WKT'):
    """Convert Labelbox JSON export to Pascal VOC format.

    Args:
        labeled_data (str): File path to Labelbox JSON export of label data.
        annotations_output_dir (str): File path of directory to write Pascal VOC
            annotation files.
        images_output_dir (str): File path of directory to write images.
        label_format (str): Format of the labeled data.
            Valid options are: "WKT" and "XY", default is "WKT".
    """

    # make sure annotation output directory is valid
    try:
        annotations_output_dir = os.path.abspath(annotations_output_dir)
        assert os.path.isdir(annotations_output_dir)
    except AssertionError as exc:
        LOGGER.exception('Annotation output directory does not exist, please create it first.')
        raise exc

    # read labelbox JSON output
    with open(labeled_data, 'r') as file_handle:
        lines = file_handle.readlines()
        label_data = json.loads(lines[0])

    for data in label_data:
        try:
            write_label(
                images_input_dir,
                data['ID'],
                data['Labeled Data'],
                data['Label'],
                label_format,
                images_output_dir,
                annotations_output_dir)

        except requests.exceptions.MissingSchema as exc:
            LOGGER.warning(exc)
            continue
        except requests.exceptions.ConnectionError:
            LOGGER.warning('Failed to fetch image from %s, skipping', data['Labeled Data'])
            continue


def write_label(  # pylint: disable-msg=too-many-arguments
        images_input_dir: str, label_id: str, image_url: str, labels: Dict[str, Any], label_format: str,
        images_output_dir: str, annotations_output_dir: str):
    """Writes a single Pascal VOC formatted image and label pair to disk.

    Args:
        label_id: ID for the instance to write
        image_url: URL to download image file from
        labels: Labelbox formatted labels to use for generating annotation
        label_format: Format of the labeled data. Valid options are: "WKT" and
                      "XY", default is "WKT".
        annotations_output_dir: File path of directory to write Pascal VOC
                                annotation files.
        images_output_dir: File path of directory to write images.
    """
    #find image
    url_list = image_url.split("/")
    image_input_fqn = os.path.join(
        images_input_dir,
        '{image_dir}/{filename}'.format(image_dir=url_list[-2], filename=url_list[-1]))
    
    image = Image.open(image_input_fqn)

    image_fqn = os.path.join(
        images_output_dir,
        '{img_id}.{ext}'.format(img_id=label_id, ext=image.format.lower()))
    
    image.save(image_fqn, format=image.format)
    
    print(image_fqn)

    # resize the image
    width, height = 300, 300
    x_factor, y_factor, pad_top = resize_image(image_fqn, width, height)

    # generate image annotation in Pascal VOC
    xml_writer = PascalWriter(image_fqn, width, height)

    # remove classification labels (Skip, etc...)
    if not callable(getattr(labels, 'keys', None)):
        # skip if no categories (e.g. "Skip")
        return

    # convert label to Pascal VOC format
    for category_name, paths in labels.items():
        if label_format == 'WKT':
            xml_writer = _add_pascal_object_from_wkt(
                xml_writer, wkt_data=paths, label=category_name)
        elif label_format == 'XY':
            xml_writer = _add_pascal_object_from_xy(xml_writer, polygons=paths, label=category_name, x_factor=x_factor, y_factor=y_factor, pad_top=pad_top)
        else:
            exc = UnknownFormatError(label_format=label_format)
            logging.exception(exc.message)
            raise exc

    # write Pascal VOC xml annotation for image
    xml_writer.save(os.path.join(annotations_output_dir, '{}.xml'.format(label_id)))


def _add_pascal_object_from_wkt(xml_writer, wkt_data, label):
    polygons = []
    if isinstance(wkt_data, list):  # V3+
        polygons = map(lambda x: wkt.loads(x['geometry']), wkt_data)
    else:  # V2
        polygons = wkt.loads(wkt_data)

    for point in polygons:
        xy_coords = []
        for x_val, y_val in point.exterior.coords:
            xy_coords.extend([x_val, y_val])
        # remove last polygon if it is identical to first point
        if xy_coords[-2:] == xy_coords[:2]:
            xy_coords = xy_coords[:-2]
        xml_writer.add_object(name=label, xy_coords=xy_coords)
    return xml_writer


def _add_pascal_object_from_xy(xml_writer, polygons, label, x_factor, y_factor, pad_top):
    if not isinstance(polygons, list):
        LOGGER.warning('polygons is not [{geometry: [xy]}] nor [[xy]], skipping')
        return xml_writer
    for polygon in polygons:
        if 'geometry' in polygon:  # V3
            polygon = polygon['geometry']
        if not isinstance(polygon, list) \
                or not all(map(lambda p: 'x' in p and 'y' in p, polygon)):
            LOGGER.warning('Could not get an point list to construct polygon, skipping')
            return xml_writer

        xy_coords = []
        for point in polygon:
            xy_coords.extend([point['x']/x_factor, ((point['y']/y_factor)+pad_top)])
        xml_writer.add_object(name=label, xy_coords=xy_coords)
    return xml_writer

def resize_image(image_path, required_img_height, required_img_width):

        img = cv2.imread(image_path)

        height, width = img.shape[:2]

        aspect_ratio = float(width)/height

        scaled_height = required_img_height
        scaled_width = required_img_width

        # interpolation method
        if height > scaled_height or width > scaled_width:  # shrinking image
            interp = cv2.INTER_AREA
        else:  # stretching image
            interp = cv2.INTER_CUBIC

        # aspect ratio of image

        # compute scaling and pad sizing
        if aspect_ratio > 1:  # horizontal image
            new_width = scaled_width
            new_height = np.round(new_width/aspect_ratio).astype(int)
            pad_vert = (scaled_height-new_height)/2
            pad_top, pad_bot = np.floor(
                pad_vert).astype(int), np.ceil(pad_vert).astype(int)
            pad_left, pad_right = 0, 0
        elif aspect_ratio < 1:  # vertical image
            new_height = scaled_height
            new_width = np.round(new_height*aspect_ratio).astype(int)
            pad_horz = (scaled_width-new_width)/2
            pad_left, pad_right = np.floor(
                pad_horz).astype(int), np.ceil(pad_horz).astype(int)
            pad_top, pad_bot = 0, 0
        else:  # square image
            new_height, new_width = scaled_height, scaled_width
            pad_left, pad_right, pad_top, pad_bot = 0, 0, 0, 0

        # factors to scale bounding box values
        x_factor = float(width) / required_img_width
        y_factor = float(height) / (required_img_height - pad_bot - pad_top)

        # set pad color
        # color image but only one color provided
        if len(img.shape) is 3 and not isinstance(0, (list, tuple, np.ndarray)):
            padColor = [0]*3

        # scale and pad
        scaled_img = cv2.resize(img, (new_width, new_height), interpolation=interp)
        scaled_img = cv2.copyMakeBorder(
            scaled_img, pad_top, pad_bot, pad_left, pad_right, borderType=cv2.BORDER_CONSTANT, value=0)

        cv2.imwrite(image_path, scaled_img)
        LOGGER.info('Resized image at {}'.format(
            image_path))
        
        return x_factor, y_factor, pad_top
