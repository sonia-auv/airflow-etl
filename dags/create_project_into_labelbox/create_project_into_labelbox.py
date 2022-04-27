import json
import uuid
import logging
from graphqlclient import GraphQLClient

logging.getLogger().setLevel(logging.INFO)


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


def __get_users(client):
    res_str = client.execute(
        """
    query GetUsersInformations {
        users {
          email
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


def __get_available_roles(client):

    res_str = client.execute(
        """
     query GetAvailableRoles {
        roles {
          name
          id
        }
      }
    """
    )

    res = json.loads(res_str)

    return res["data"]["roles"]


def __get_specific_role_id(client, role_name):
    roles = __get_available_roles(client)

    for role in roles:
        if role_name == role["name"]:
            return role["id"]

    raise ValueError(f"Role:{role_name} is invalid")


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

    ti = kwargs["ti"]
    ti.xcom_push(key="labebox_project_dataset_id", value=res["data"]["createDataset"]["id"])


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

    ti = kwargs["ti"]
    ti.xcom_push(
        key="labebox_project_labeling_interface_id", value=res["data"]["labelingFrontends"][0]["id"]
    )


def configure_interface_for_project(api_url, api_key, ontology, index, **kwargs):
    client = __get_client(api_url, api_key)
    organization_id = __get_organization_id(client)

    ti = kwargs["ti"]

    project_id = ti.xcom_pull(
        key="labebox_project_id", task_ids=f"task_create_project_into_labelbox_{index}"
    )
    interface_id = ti.xcom_pull(
        key="labebox_project_labeling_interface_id",
        task_ids=f"task_get_labeling_image_interface_from_labelbox_{index}",
    )

    organization_id = __get_organization_id(client)

    # print(json.dumps(ontology))
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
            "customizationOptions": ontology,  # json.dumps(ontology),
            "labelingFrontendId": interface_id,
            "organizationId": organization_id,
        },
    )

    res = json.loads(res_str)
    print(res)


def complete_project_setup(api_url, api_key, index, **kwargs):
    client = __get_client(api_url, api_key)

    ti = kwargs["ti"]

    project_id = ti.xcom_pull(
        key="labebox_project_id", task_ids=f"task_create_project_into_labelbox_{index}"
    )

    dataset_id = ti.xcom_pull(
        key="labebox_project_dataset_id", task_ids=f"task_create_dataset_into_labelbox_{index}"
    )

    labeling_frontend_id = ti.xcom_pull(
        key="labebox_project_labeling_interface_id",
        task_ids=f"task_get_labeling_image_interface_from_labelbox_{index}",
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
    # TODO: Handle error
    print("Labelbox project setup complete")


def create_data_rows(api_url, api_key, index, json_file, **kwargs):

    with open(json_file) as f:
        data = json.load(f)

        client = __get_client(api_url, api_key)
        ti = kwargs["ti"]

        dataset_id = ti.xcom_pull(
            key="labebox_project_dataset_id", task_ids=f"task_create_dataset_into_labelbox_{index}"
        )

        for item in data:
            for attempt in range(10):
                try:

                    external_id = uuid.uuid1()
                    res_str = client.execute(
                        """
                      mutation createDataRowFromAPI(
                      $image_url: String!, $external_id: String!, $dataset_id: ID!) {
                        createDataRow(
                          data: {
                            rowData: $image_url
                            externalId: $external_id
                            dataset: { connect: { id: $dataset_id } }
                          }
                        ){
                        id
                        }
                      }
                      """,
                        {
                            "dataset_id": dataset_id,
                            "image_url": item["imageUrl"],
                            "external_id": str(external_id),
                        },
                    )
                    print(res_str)
                    res = json.loads(res_str)
                    print(f"Data row added: {item['imageUrl']} - ID : {res['data']['createDataRow']['id']}")

                except Exception as error:
                    print(f"The connection has failed // {error}")
                else:
                    break
        print("Added all row to dataset")


def add_users_to_project(api_url, api_key, index, users, **kwargs):
    client = __get_client(api_url, api_key)
    ti = kwargs["ti"]

    project_id = ti.xcom_pull(
        key="labebox_project_id", task_ids=f"task_create_project_into_labelbox_{index}"
    )

    for user in users:
        email = user["email"]
        name = user["name"]
        role = user["role"]

        print(f"Adding user to project: User:{name}, Email:{email}, Role:{role}")

        role_id = __get_specific_role_id(client, role)

        print(f"Adding user to project: User:{name}, Email:{email}, Role:{role}, RoleID: {role_id}")

        res_str = client.execute(
            """
            mutation AddUserToProject {
              addUserToProject(
                data: {
                  email: "$email",
                  projectId: "$projectId",
                  roleId: "$roleId"
                }
              ) {
                user { email }
                project { name }
                role { name }
              }
              }
            """,
            {"email": email, "projectId": project_id, "roleId": role_id},
        )

        res = json.loads(res_str)
        print(res)
