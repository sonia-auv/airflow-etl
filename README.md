# S.O.N.I.A's ETL

This is S.O.N.I.A's ETL engine to orchestrate our machine learning jobs
using [Apache-Airflow](https://airflow.apache.org/)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

```bash
$ git clone https://github.com/sonia-auv/docker-ros-airflow
```

### Prerequisites

You must create a [Dockerhub](https://hub.docker.com/signup) account.

Then you must have been granted collaborator access on the club.sonia@etstml.net

First of all you must have docker and docker-composed install on your system using the provided links
[Docker installation](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04)
[Docker-Compose installation](https://www.digitalocean.com/community/tutorials/how-to-install-docker-compose-on-ubuntu-18-04)

When you have completed docker and docker-compose installation you must login into your terminal using the following commmand

```bash
docker login
```

### Installation

#### Development environment


##### Environment file

After you have installed docker and docker-compose you must create an environment file. Simply copy .env.template with destination file name .env

```
cp .env.template .env
```

#### Google Cloud SDK
When you have successfully launched the containers you must set your credential too google cloud.
To complete this step you must ask for access either to the captain or software rep to the required access.

You must execute the following commands to init you gcloud config:

```bash
docker exec -it sonia-auv-airflow_airflow-webserver_1 gcloud init
```

You will the be asked to select your google account using a link that will displayed in the terminal.

Afterward you will need to input the verification code into the terminal.

Once it's done you should be prompted to input the project name which should be *deep-learning-detection*

And you must set you default region to *us-east-1-c*

#### Airflow UI User

To create a user to access the Airflow UI through a web browser you must run the following command
```bash
docker exec -it sonia-auv-airflow_airflow-webserver_1 airflow create_user --role Admin --username USERNAME --email EMAIL --firstname FIRSTNAME --lastname LASTNAME --password PASSWORD
```

#### Start Airflow

Once you have your configuration file, run this command in you shell:


```bash
./start.sh dev
```

This will pull the docker-ros-airflow image from the docker repository, and start the containers locally.
It will start both the airflow container as the postgres container use to store airflow metadata.

The output of the script should look like this

```bash
#########################################################################

 Generating 'soniaauvets/airflow-ros-tensorflow' image using tag '1.1.3'
1.1.3: Pulling from soniaauvets/airflow-ros-tensorflow
Digest: sha256:778224fdeb5b89a790376084913d272b87a8f24d6352af527e1b472839e7b0dd
Status: Image is up to date for soniaauvets/airflow-ros-tensorflow:1.1.3
#########################################################################

Launching sonia-auv airflow docker containers
Starting sonia-auv-airflow_airflow-postgres_1 ... done
sonia-auv-airflow_airflow-webserver_1 is ... done
#########################################################################

Airflow containers have STARTED
```

#### Production environment

##### Environment file

After you have installed docker and docker-compose you must create an environment file. Simply copy .env.template with destination file name .env

```
cp .env.template .env
```
#### Airflow Fernet Key (Database data encryption)

First of all you must generate an Fernet Key to encrypt (connexions data) into Airflow database

Here are the step to generate a fernet key

```bash
pip install cryptography
```
Then execute the following command to generate the fernet key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Replace the **AIRFLOW_FERNET_KEY** field value by the newly created key into the **.env** file

#### Launch Airflow services

```bash
./start.sh prod
```

This will pull the docker-ros-airflow image from the docker repository, and start the containers locally.
It will start both the airflow container as the postgres container use to store airflow metadata.

The output of the script should look like this

```bash
#########################################################################

 Generating 'soniaauvets/airflow-ros-tensorflow' image using tag '1.1.3'
1.1.3: Pulling from soniaauvets/airflow-ros-tensorflow
Digest: sha256:778224fdeb5b89a790376084913d272b87a8f24d6352af527e1b472839e7b0dd
Status: Image is up to date for soniaauvets/airflow-ros-tensorflow:1.1.3
#########################################################################

Launching sonia-auv airflow docker containers
Starting sonia-auv-airflow_airflow-postgres_1 ... done
sonia-auv-airflow_airflow-webserver_1 is ... done
#########################################################################

Airflow containers have STARTED
```

#### Google Cloud SDK

**NOTE:** Make sure to that the file glcoud_service_account.json exist in docker-ros-airflow/config on the VM
**NOTE:** Make sure the webserver docker container is running

Then from the vm run the following command

```bash
docker exec -it sonia-auv-airflow_airflow-webserver_1 gcloud auth activate-service-account airflow-etl-sonia@deep-learning-detection.iam.gserviceaccount.com --key-file=gcloud_service_account.json
docker exec -it sonia-auv-airflow_airflow-webserver_1 gcloud config set project deep-learning-detection && gcloud config set compute/zone us-east1 && gcloud config set compute/region us-east1-c
```

#### Airflow UI User

To create a user to access the Airflow UI through a web browser you must run the following command
```bash
docker exec -it sonia-auv-airflow_airflow-webserver_1 airflow create_user --role Admin --username USERNAME --email EMAIL --firstname FIRSTNAME --lastname LASTNAME --password PASSWORD
```

#### Airflow Variables (Variables)

To import airflow variables from saved json file you must run the following command :

```bash
docker exec -it sonia-auv-airflow_airflow-webserver_1 airflow variables --import variables.json
```

The variables file is added to the docker image during build and it's located into the config directory
It can be modified if new variables are added to the airflow instance.
Their is an airflow command to extract it see [airflow variables](https://airflow.apache.org/docs/stable/concepts.html?highlight=variable)


### Airflow connections

You must create connections into Airflow UI to be able to launch all our pipelines.

* Slack connection :[Medium Article](https://medium.com/datareply/integrating-slack-alerts-in-airflow-c9dcd155105) (see Using Slack Webhook section)

* Labelbox : Delete existing labelbox key into into the labelbox setting menu an create a new one using the club.sonia@etsmtl.net account


### Usage

### Airflow Variables
Our project defines admin variables to change the behavior and configuration of DAGS. In the Admin->Variables section of Airflow, you can import from json file. For an example of a variables set, see the variables.json file at the root of the repository.

## Troubleshooting

### Permission denied on the logs directory
This error is caused by your logs directory being owned by root. It produces the following logs(https://pastebin.com/HWpXu83w). To fix, change the owner of the root directory to the current user:

```
chown -R [user]:[user] logs
```

## Built With
- [Apache-Airflow](https://airflow.apache.org/) - Apache-Airflow

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags).

## Authors

- **Martin Gauthier** - _Initial work_ - [gauthiermartin](https://github.com/gauthiermartin)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
