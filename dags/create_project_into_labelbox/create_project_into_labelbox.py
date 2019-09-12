from airflow import DAG
import json
from graphqlclient import GraphQLClient

# client = GraphQLClient('https://api.labelbox.com/graphql')
# client.inject_token('Bearer <API-KEY-HERE>')


def _get_client(api_url, api_key):
    client = GraphQLClient(api_url)
    client.inject_token(api_key)
    return client

    # ontology = {
    #     "tools": [
    #         {
    #             "name": "jiangshi",
    #             "color": "#2A00FF",
    #             "tool": "rectangle",
    #             "featureSchemaId": "cb8ddbb0-e818-40c9-99f0-6a2ffc735d7b",
    #             "schemaNodeId": "e129fbf9-f3db-4a91-a686-6d1a5658e97b"
    #         },
    #         {
    #             "name": "draugr",
    #             "color": "#FF0000",
    #             "tool": "rectangle",
    #             "featureSchemaId": "32ff2be3-9b01-4843-ab1f-d4d4f4b0acfc",
    #             "schemaNodeId": "d6b7b829-4fb8-4cd4-a62c-c442237cc6f4"
    #         },
    #         {
    #             "name": "vetalas",
    #             "color": "#00FFFF",
    #             "tool": "rectangle",
    #             "featureSchemaId": "13319115-6011-49d9-8c16-55d75580fafc",
    #             "schemaNodeId": "a771ffb8-012b-4824-a225-72819e860c3b"
    #         }
    #     ],
    #     "classifications": []
    # }

# def me():
#     res_str = client.execute("""
#     query GetUserInformation {
#       user {
#         id
#         organization{
#           id
#         }
#       }
#     }
#     """)

#     res = json.loads(res_str)
#     return res['data']['user']


def create_dataset(api_url, api_key, name):
    client = _get_client(api_url, api_key)
    res_str = client.execute("""
    mutation CreateDatasetFromAPI($name: String!) {
      createDataset(data:{
        name: $name
      }){
        id
      }
    }
    """, {'name': name})

    res = json.loads(res_str)
    return res['data']['createDataset']['id']


def create_project(name):
    client = _get_client(api_url, api_key)
    res_str = client.execute("""
    mutation CreateProjectFromAPI($name: String!) {
      createProject(data:{
        name: $name
      }){
        id
      }
    }
    """, {'name': name})

    res = json.loads(res_str)
    return res['data']['createProject']['id']


def complete_project_setup(project_id, dataset_id, labeling_frontend_id):
    client = _get_client(api_url, api_key)
    res_str = client.execute("""
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
    """, {
        'projectId': project_id,
        'datasetId': dataset_id,
        'labelingFrontendId': labeling_frontend_id
    })

    res = json.loads(res_str)
    return res['data']['updateProject']['id']


def configure_interface_for_project(ontology, project_id, interface_id, organization_id):
    client = _get_client(api_url, api_key)
    res_str = client.execute("""
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
    """, {
        'projectId': project_id,
        'customizationOptions': json.dumps(ontology),
        'labelingFrontendId': interface_id,
        'organizationId': organization_id,
    })

    res = json.loads(res_str)
    return res['data']['createLabelingFrontendOptions']['id']


def get_image_labeling_interface_id():
    client = _get_client(api_url, api_key)
    res_str = client.execute("""
      query GetImageLabelingInterfaceId {
        labelingFrontends(where:{
          iframeUrlPath:"https://image-segmentation-v4.labelbox.com"
        }){
          id
        }
      }
    """)

    res = json.loads(res_str)
    return res['data']['labelingFrontends'][0]['id']


# def create_datarow(row_data, external_id, dataset_id):
#     client = _get_client(api_url, api_key)
#     res_str = client.execute("""
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
#     """, {
#         'rowData': row_data,
#         'externalId': external_id,
#         'datasetId': dataset_id
#     })

#     res = json.loads(res_str)
#     return res['data']['createDataRow']['id']
"""
 This DAG will handle project creation into labelbox
"""
