#Docker(ROS-Airflow-Google Cloud SDK)

This module is S.O.N.I.A's object detection module using our vison server based on [ROS](http://www.ros.org/)

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

#### .env file

After you have installed docker and docker-compose you must create an environment file. Simply copy .env.template with destination file name .env

```
cp .env.template .env
```

#### start.sh script

Once you have your configuration file, run this command in you shell:


```bash
./start.sh
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

When you have successfully launched the containers you must set your credential too google cloud.
To complete this step you must ask for access either to Marc-Antoine or Martin

You must execute the following commands to init you gcloud config:

```bash
docker exec -it sonia-auv-airflow_airflow-webserver_1 gcloud init
```

You will the be asked to select your google account using a link that will displayed in the terminal.

Afterward you will need to input the verification code into the terminal.

Once it's done you should be prompted to input the project name which should be *deep-learning-detection*

And you must set you default region to *us-east-1-c*

#### add slack connection

You need to add a slack connection to be able to use slack in airflow.

### Usage

#### Extract bags img from bags(extract_img_from_ros_bag_dag)
1. Create a directory that will contain your bags in the `data/input/ros_bag` directory
2. Add your bag in the folder
3. Launch the extract_img_from_ros_bag DAG


### Admin Variables
Our project defines admin variables to change the behavior and configuration of DAGS. In the Admin->Variables section of Airflow, you can import from json file. For an example of a variables set, see the variables.json file at the root of the repository.

#### Dataset
Represents the name of the bag you want to extract into a series of images. The dataset variable is also used for naming the output images folder

### Bucket
link to the targeted bucket. See variables.json for an example.

### Dataset_to_Trainset
Comma-separated list of Dataset to convert into Trainset. See variables.json for an example.

### Trainset
Represent the name of your final tf_record directory. See variables.json for an example.

#### Topics
Comma-separated list of ROS Topics that the images will be extracted from. See variables.json for an example.

### Before generating tf_record file
before generating the tf_record file be sure to have the label_map file, it must have the name `<name of your Trainset>.pbtxt` for an example
of label_map file refer to this [file](https://github.com/EdjeElectronics/TensorFlow-Object-Detection-API-Tutorial-Train-Multiple-Objects-Windows-10/blob/master/training/labelmap.pbtxt)


#### Developpement

## Deployment

Add additional notes about how to deploy this on a live system

## Troubleshooting

### Permission denied on the logs directory
This error is caused by your logs directory being owned by root. It produces the following logs(https://pastebin.com/HWpXu83w). To fix, change the owner of the root directory to the current user:

```
chown -R [user]:[user] logs
```

## Built With

- [ROS](http://www.ros.org/) - ROS Robotic Operating System
- [TENSORFLOW](http://tensorflow.com) - Tensorflow Deep learning library

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags).

## Authors

- **Martin Gauthier** - _Initial work_ - [gauthiermartin](https://github.com/gauthiermartin)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

- This repository is highly inspred on [GustavZ repository](https://github.com/GustavZ?tab=repositories) Original part used from this project are still copyrighted by him. Such part have been identified in our code.
