import json
from graphqlclient import GraphQLClient

# client = GraphQLClient('https://api.labelbox.com/graphql')
# client.inject_token('Bearer <API-KEY-HERE>')


def _get_client(api_url, api_key):
    client = GraphQLClient(api_url)
    client.inject_token(api_key)
    return client


def _create_ontology():
    pass
    # TODO: create anthology

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


def createDataset(api_url, api_key, name):
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


def createProject(name):
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


def completeSetupOfProject(project_id, dataset_id, labeling_frontend_id):
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
