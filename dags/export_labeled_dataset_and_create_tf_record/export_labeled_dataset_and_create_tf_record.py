import json
import os
import shutil
import time
import urllib.request
from xml.etree import ElementTree as ET

from graphqlclient import GraphQLClient

from utils import file_ops


def __get_client(api_url, api_key):
    api_token = "Bearer " + api_key
    client = GraphQLClient(api_url)
    client.inject_token(api_token)

    return client


def __get_projects(client):
    res_str = client.execute(
        """
    query GetAProjectFromOrganization {
      projects {
        id
        name
        deleted
      }
    }
    """
    )
    res = json.loads(res_str)
    new_res = []
    for project in res["data"]["projects"]:
        if not project["deleted"]:
            new_res.append(project)
    print(new_res)
    return new_res


def __get_specific_project_id(client, project_name):

    projects = __get_projects(client)

    for project in projects:
        if project["name"] == project_name:
            return project["id"]
    raise ValueError("Project name not found")


def __get_export_url(client, project_id):
    print(project_id)
    res_str = client.execute(
        """
    mutation GetExportUrl($project_id: ID!){
      exportLabels(data:{
        projectId: $project_id
      }){
        downloadUrl
        createdAt
        shouldPoll
      }
    }
    """,
        {"project_id": project_id},
    )
    print(res_str)
    res = json.loads(res_str)
    return res["data"]["exportLabels"]


def generate_project_labels(api_url, api_key, project_name):
    client = __get_client(api_url, api_key)
    print("generate labels: " + project_name)
    project_id = __get_specific_project_id(client, project_name)
    export_job = __get_export_url(client, project_id)
    if export_job["shouldPoll"]:
        print("Export Generating...")


def fetch_project_labels(api_url, api_key, project_name, output_folder):
    client = __get_client(api_url, api_key)
    project_id = __get_specific_project_id(client, project_name)
    export_job = __get_export_url(client, project_id)
    print("Fetching payload .....")

    with urllib.request.urlopen(export_job["downloadUrl"]) as url:
        labels = json.loads(url.read().decode())
        print(labels)
        folder = os.path.join(output_folder, "input", project_name)
        output_folder = os.path.join(output_folder, "output", project_name)

        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)

        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)

        json_file = f"{folder}/{project_name}.json"
        if os.path.exists(json_file):
            os.remove(json_file)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=4)


def generate_trainval_file(annotation_dir, output_dir, output_file):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    trainval_file_path = os.path.join(output_dir, f"{output_file}.txt")
    xml_files = file_ops.get_files_in_directory(annotation_dir, "*.xml")
    with open(trainval_file_path, "w") as outfile:
        for xml_file in xml_files:
            filename = file_ops.get_filename(xml_file, with_extension=False)
            outfile.write(filename + "\n")


def generate_labelmap_file(labels, output_dir, output_file):
    data = []
    # first_line = "item {\n"
    # second_line = "  id: {}\n"
    # third_line = "  name: '{}'\n"
    # fourth_line = "}"

    for index, label_name in enumerate(labels):
        first_line = "item {\n"
        second_line = "  id: {}\n".format(index + 1)
        third_line = "  name: '{}'\n".format(label_name)
        fourth_line = "}\n"

        temp = first_line + second_line + third_line + fourth_line
        data.append(temp)

    file_path = os.path.join(output_dir, f"{output_file}.pbtxt")

    with open(file_path, "w") as label_file:
        label_file.writelines(data)
