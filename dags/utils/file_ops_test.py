import os
import unittest

import file_ops

class FileOptsTest(unittest.TestCase):

    def test_gcs_path_to_local_path(self):
        test_path = "gs://bucket-name/dataset/image"
        expected_path = "/ROOT_LOCATION/images_folder/dataset/image"

        images_path = "/ROOT_LOCATION/images_folder"

        path = file_ops.gcs_path_to_local_path(images_path, test_path)

        self.assertEqual(path, expected_path)

if __name__ == "__main__":
    unittest.main()