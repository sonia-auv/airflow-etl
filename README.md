#Docker(ROS-Airflow-Google Cloud SDK)

This module is S.O.N.I.A's object detection module using our vison server based on [ROS](http://www.ros.org/)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

```bash
$ git clone https://github.com/sonia-auv/docker-ros-airflow
```

### Prerequisites

You must install S.O.N.I.A's ROS repostitories to use this module.

S.O.N.I.A's installation instruction are available at [SONIA's Installation](https://sonia-auv.readthedocs.io/user/installation/)

### Installing

First of all you must have docker and docker-composed install on your system using the provided links
[Docker installation](https://docs.docker.com/install/linux/docker-ce/ubuntu/)
[Docker-Compose installation](https://docs.docker.com/compose/install/)


After you have installed docker and docker-compose you must run this command in you shell.
This will pull the docker-ros-airflow image from the docker repository, and start the containers locally.

```bash
./start.sh
```

#TODO: Gcloud config init
#TODO: Start server and ssh into it
#TODO: Shutdown server


#### Developpement

## Deployment

Add additional notes about how to deploy this on a live system

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
