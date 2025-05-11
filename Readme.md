<div align="center">
  <h1 style="padding:15px;border-bottom: 0;">CLUE: Cloud-native Sustainability Evaluator</h1>
</div>

## 📢 About the Project

Clue is  a benchmarking and observability framework for gathering and compiling sustainability and quality reports on changes in cloud-native applications. 

It can be used as part of your CI/CD pipeline to evaluate the impact of changes or as a standalone tool to evaluate prototypes you are working on.

The framework is designed to be extensible and can be easily integrated with existing cloud providers. We currently rely on Prometheus to collect all relevant metrics, but we are working on adding support for other monitoring tools. 
Moreover, we are currently focusing on Kubernetes as the orchestrator, so as long as your application runs on Kubernetes, you can use Clue to evaluate it. However, we are working on adding support for other environments as well.

This Readme describes the process of running experiments on different variants of the TeaStore microservice example.

### Quicklinks

- [Prerequisites](prerequisites)
- [System Setup](#1-system-setup)
  - [Setting up the image registry]()
  - [Setting up Prometheus]()
  - [CLUE2 deployer setup]()
  - [Manually running a single variant (for debugging purposes)](#2-manually-running-a-single-variant-for-debugging-purposes)
  - [Testing the experiment setup (without building images)](#3-testing-the-experiment-setup-without-building-images)
  - [Running the experiments (with building and pushing images)](#4-running-the-experiments-with-building-and-pushing-images)
- [Troubleshooting / Known Issues](#troubleshooting--known-issues)

## 📦 Prerequisites

  * Docker, e.g. 20.10
  * Kubernetes, e.g. 1.29 (for testing purposes, [minikube](https://minikube.sigs.k8s.io/docs/) works)
    * at least one Kubernetes node running Scaphandra/[Kepler](https://sustainable-computing.io/installation/kepler-helm/), and a [NodeExporter](https://observability.thomasriley.co.uk/monitoring-kubernetes/metrics/node-exporter/). If the tracker does not find any energy data, the experiment will start, but the script will stop due to lack of usable insights
    * for the serverless variant, knative installed
    * for external power meters, connect e.g. a Tapo device (out of scope of this Readme)
  * [Helm](https://helm.sh/), e.g. v3.16
  * Python, e.g. 3.11, using uv in this Readme


## 🚀 System Setup

> [!CAUTION]
> Please note that this repository also contains work in progress parts -- not all CLUE features and experiment branches that are not mentioned in the paper might be thoroughly tested.

### 1. Setting up the image registry

First make sure `Docker` (with `Docker Compose` support) is installed and running, then execute this command to spin up the image registry:

```bash
docker compose up -d
```

Update the `Docker Deamon` configuration to allow insecure connections to the deployed image registry. For `Docker Desktop` go to the configuration and the `Docker Engine` tab and append the following option:

```json
  "insecure-registries": [
    "host.docker.internal:6789"
  ]
```

Make sure that `Minikube` (or your other choosen local kubernets cluster) accepts the registry as well and has enough memory (configure docker before). In case you already have created a minikube cluster before make sure to delete if and recreate it using this command:

```bash
minikube start --cni=flannel --insecure-registry "host.docker.internal:6789" --cpus 8 --memory 12000
```

Also add an additional node to allow running the loadgenerator (which can not run on the same node as the experiment itself):

```bash
minikube node add
```

### 2. CLUE2 setup
Clone the system under test, i.e. the teastore. Each variant is in a separate branch.

```bash
git clone https://github.com/ISE-TU-Berlin/sustainable_teastore.git teastore
```

For local development, clone the PSC tracker into `agent` (uv is configured in the toml to find it there):

```bash
git clone https://github.com/ISE-TU-Berlin/PSC.git agent
```

Install Python dependencies using [uv](https://docs.astral.sh/uv/) (or use a virtual environment with e.g. pipenv)

```bash
uv sync
```

In a multi-node setting, not all nodes might have the option to measure using scaphandre, so Clue ensures that only appropiate nodes are assigned with experiment pods. To simulate this for, e.g., the minikube node, apply a label:

```bash
kubectl label nodes minikube scaphandre=true
```

### 2. CLUE2 building

In order to deploy or run an experiment first the images have to be built. Adjust the configs according to your setup and run this command to built all required images for your experiments:

```bash
python python clue-builders/teastore/build.py
```

### 3. CLUE2 deploying

For deploying (without the laodgenerator) an experiment to your cluster, run the following command. Make sure to build the images before.

```bash
python python clue-deployer/run.py --sut teastore --exp-name baseline
```

When using minikube, forward a port so you can access the TeaStore:

```bash
kubectl port-forward service/teastore-webui 8080:80 --namespace=tea-bench
```

TeaStore may run some initial tasks on startup, so make sure to wait a minute if is slow / unavailable (for experiments, this is handled through a waiting period as well)

![TeaStore in the Browser](readme/teastore_jvm.png)

### 4. Testing the experiment setup (without building images)

This will run the experiments from `exv2/experiment_list.py` and gather the results.
Without building images, Clue will use the latest images from the public registry, not necessarily the variant checked out locally!

```bash
python exv2/main.py --skip-build
```

![Running the Experiments](readme/running_experiments.png)

### 6. Running the experiments (with building and pushing images)

If you create your own variants or make changes, the images need to be rebuilt and pushed to a registry.

 * Adapt `exv2/experiment_environment.py` to contain your docker registry url
 * Make sure to run docker login in case authentication is needed

If all the preliminaries for data collection are installed, Clue will fetch the relevant measuremens from Prometheus and save them into the data folder. For data analysis, we provide Python notebooks seperately.


## 💻 Troubleshooting / Known Issues

 * When using docker desktop, enable in settings > advanced: *Allow the default Docker socket to be used*
 * Ensure that you have a sufficient amount of memory alocated for docker, at least 12 GB
 * Run `minikube dashboard` to monitor deployment errors, e.g. missing node labels or insufficient memory
 * The monolith app has some specific handles, e.g. a different set name. If a a set is not found, especially when skipping builds, this can cause probelems