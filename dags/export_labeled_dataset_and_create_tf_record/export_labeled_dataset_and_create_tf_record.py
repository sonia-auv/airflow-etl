import os
import json
import shutil
import time
import urllib.request
from graphqlclient import GraphQLClient


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
      }
    }
    """
    )

    res = json.loads(res_str)
    return res["data"]["projects"]


def __get_specific_project_id(client, project_name):

    projects = __get_projects(client)

    for project in projects:
        if project["name"] == project_name:
            return project["id"]
    raise ValueError("Project name not found")


def __get_export_url(client, project_id):
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
    res = json.loads(res_str)
    return res["data"]["exportLabels"]


def generate_project_labels(api_url, api_key, project_name):
    client = __get_client(api_url, api_key)
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
        folder = os.path.join(output_folder, project_name)

        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.mkdir(folder)

        json_file = f"{folder}/{project_name}.json"
        if os.path.exists(json_file):
            os.remove(json_file)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=4)
