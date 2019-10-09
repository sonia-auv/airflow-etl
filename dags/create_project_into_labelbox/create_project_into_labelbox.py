import json
from graphqlclient import GraphQLClient


def __get_client(api_url, api_key):
    api_token = "Bearer " + api_key
    client = GraphQLClient(api_url)
    client.inject_token(api_token)

    return client


def __get_user_info(client):
    res_str = client.execute(
        """
    query GetUserInformation {
      user {
        id
        organization{
          id
        }
      }
    }
    """
    )

    res = json.loads(res_str)
    return res["data"]["user"]


def __get_organization_id(client):
    user_info = __get_user_info(client)
    org_id = user_info["organization"]["id"]
    return org_id


def create_project(api_url, api_key, project_name, **kwargs):
    client = __get_client(api_url, api_key)
    res_str = client.execute(
        """
    mutation CreateProjectFromAPI($name: String!) {
      createProject(data:{
        name: $name
      }){
        id
      }
    }
    """,
        {"name": project_name},
    )

    res = json.loads(res_str)

    # return res["data"]["createProject"]["id"]
    ti = kwargs["ti"]
    ti.xcom_push(key="labebox_project_id", value=res["data"]["createProject"]["id"])


def create_dataset(api_url, api_key, project_name, dataset_name, **kwargs):
    client = __get_client(api_url, api_key)
    res_str = client.execute(
        """
    mutation CreateDatasetFromAPI($name: String!) {
      createDataset(data:{
        name: $name
      }){
        id
      }
    }
    """,
        {"name": dataset_name},
    )

    res = json.loads(res_str)

    # return res["data"]["createDataset"]["id"]

    ti = kwargs["ti"]
    ti.xcom_push(key="labebox_project_dataset_id", value=res["data"]["createProject"]["id"])


def get_image_labeling_interface_id(api_url, api_key, **kwargs):
    client = __get_client(api_url, api_key)
    res_str = client.execute(
        """
      query GetImageLabelingInterfaceId {
        labelingFrontends(where:{
          iframeUrlPath:"https://image-segmentation-v4.labelbox.com"
        }){
          id
        }
      }
    """
    )

    res = json.loads(res_str)

    return res["data"]["labelingFrontends"][0]["id"]

    ti = kwargs["ti"]
    ti.xcom_push(
        key="labebox_project_labeling_interface_id", value=res["data"]["labelingFrontends"][0]["id"]
    )


def configure_interface_for_project(api_url, api_key, ontology, index, **kwargs):
    client = __get_client(api_url, api_key)
    organization_id = __get_organization_id(client)

    ti = kwargs["ti"]

    project_id = ti.xcom_pull(
        key="labebox_project_id", task_id=f"task_create_project_into_labelbox_{index}"
    )
    interface_id = ti.xcom_pull(
        key="labebox_project_labeling_interface_id",
        task_id=f"task_get_labeling_image_interface_from_labelbox_{index}",
    )

    organization_id = __get_organization_id(client)

    res_str = client.execute(
        """
      mutation ConfigureInterfaceFromAPI($projectId: ID!, $customizationOptions: String!, $labelingFrontendId: ID!, $organizationId: ID!) {
        createLabelingFrontendOptions(data:{
          customizationOptions: $customizationOptions,
          project:{
            connect:{
              id: $projectId
            }
          }
          labelingFrontend:{
            connect:{
              id:$labelingFrontendId
            }
          }
          organization:{
            connect:{
              id: $organizationId
            }
          }
        }){
          id
        }
      }
    """,
        {
            "projectId": project_id,
            "customizationOptions": json.dumps(ontology),
            "labelingFrontendId": interface_id,
            "organizationId": organization_id,
        },
    )

    res = json.loads(res_str)

    ti.xcom_push(
        key="labebox_labeling_frontend_id", value=res["data"]["createLabelingFrontendOptions"]["id"]
    )


def complete_project_setup(api_url, api_key, index, **kwargs):
    client = __get_client(api_url, api_key)

    ti = kwargs["ti"]

    project_id = ti.xcom_pull(
        key="labebox_project_id", task_id=f"task_create_project_into_labelbox_{index}"
    )

    dataset_id = ti.xcom_pull(
        key="labebox_project_dataset_id", task_id=f"task_create_dataset_into_labelbox_{index}"
    )

    labeling_frontend_id = ti.xcom_pull(
        key="labeling_frontend_id",
        task_id=f"task_configure_labeling_interface_for_project_into_labelbox_{index}",
    )

    res_str = client.execute(
        """
    mutation CompleteSetupOfProject($projectId: ID!, $datasetId: ID!, $labelingFrontendId: ID!){
      updateProject(
        where:{
          id:$projectId
        },
        data:{
          setupComplete: "2018-11-29T20:46:59.521Z",
          datasets:{
            connect:{
              id:$datasetId
            }
          },
          labelingFrontend:{
            connect:{
              id:$labelingFrontendId
            }
          }
        }
      ){
        id
      }
    }
    """,
        {
            "projectId": project_id,
            "datasetId": dataset_id,
            "labelingFrontendId": labeling_frontend_id,
        },
    )

    res = json.loads(res_str)

    # TODO: Do we need the updated id here ????
    return res["data"]["updateProject"]["id"]


# def create_datarow(api_url, api_key, row_data, external_id, dataset_id):
#     client = __get_client(api_url, api_key)

#     res_str = client.execute(
#         """
#       mutation CreateDataRowFromAPI(
#         $rowData: String!,
#         $externalId: String,
#         $datasetId: ID!
#       ) {
#         createDataRow(data:{
#           externalId: $externalId,
#           rowData: $rowData,
#           dataset:{
#             connect:{
#               id: $datasetId
#             }
#           }
#         }){
#           id
#         }
#       }
#     """,
#         {"rowData": row_data, "externalId": external_id, "datasetId": dataset_id},
#     )

#     res = json.loads(res_str)
#     # return res["data"]["createDataRow"]["id"]


# def bulk_import_datastet(dataSetId, jsonFileURL):
#     """ returns true if upload was successful.
#       See the documentation for more informaton:
#       https://labelbox.com/docs/api/data-import
#   """
#     res_str = client.execute(
#         """
#   mutation AppendRowsToDataset($dataSetId : ID!, $jsonURL: String!){
#     appendRowsToDataset(
#       data:{
#         datasetId: $dataSetId,
#         jsonFileUrl: $jsonURL
#       }
#     ){
#       accepted
#     }
#   } """,
#         {"dataSetId": dataSetId, "jsonURL": jsonFileURL},
#     )

#     res = json.loads(res_str)
#     return res["data"]["appendRowsToDataset"]["accepted"]
