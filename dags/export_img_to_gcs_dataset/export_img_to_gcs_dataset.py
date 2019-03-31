import os
import logging
import csv

def create_csv(images_path, gcs_images_path, dataset, csv_path):
    # Create array of image urls in GCS
    file_names = os.listdir(os.path.join(images_path, dataset))
    urls = list(map(lambda x: os.path.join(gcs_images_path, x), file_names))

    # Export CSV
    csv_file_path = os.path.join(csv_path, dataset)
    with open(csv_file_path + ".csv", 'wb') as csv_file:
        writer = csv.writer(csv_file, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Image_URL'])
        map(lambda x: writer.writerow([x]), urls)