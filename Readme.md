<div align="center">
  <h1 style="padding:15px;border-bottom: 0;">CLUE: Cloud-native Sustainability Evaluator</h1>
</div>

## 📢 About the Project

Clue is  a benchmarking and observability framework for gathering and compiling sustainability and quality reports on changes in cloud-native applications. 

It can be used as part of your CI/CD pipeline to evaluate the impact of changes or as a standalone tool to evaluate prototypes you are working on.

The framework is designed to be extensible and can be easily integrated with existing cloud providers. We currently rely on Prometheus to collect all relevant metrics, but we are working on adding support for other monitoring tools. 
Moreover, we are currently focusing on Kubernetes as the orchestrator, so as long as your application runs on Kubernetes, you can use Clue to evaluate it. However, we are working on adding support for other environments as well.

This Readme describes the process of running CLUE experiments on the selected SUT.

## 📦 Prerequisites

  * Docker, e.g. 20.10
  * Kubernetes, e.g. 1.29 (for testing purposes, [minikube](https://minikube.sigs.k8s.io/docs/) works)
    * at least one Kubernetes node running Scaphandra/[Kepler](https://sustainable-computing.io/installation/kepler-helm/), and a [NodeExporter](https://observability.thomasriley.co.uk/monitoring-kubernetes/metrics/node-exporter/). If the tracker does not find any energy data, the experiment will start, but the script will stop due to lack of usable insights
    * for the serverless variant, knative installed
    * for external power meters, connect e.g. a Tapo device (out of scope of this Readme)
  * [Helm](https://helm.sh/), e.g. v3.16
  * Python, e.g. 3.11, using uv in this Readme


## 🚀 System setup

> [!CAUTION]
> Please note that this repository also contains work in progress parts -- not all CLUE features and experiment branches that are not mentioned in the paper might be thoroughly tested.

### 1. 🏁 Setting up the image registry

The docker image registry used by CLUE can be specified in the `clue-config.yaml` file (`docker_registry_address` parameter). By default, CLUE supports deploying a local image registry listed below. To deploy the local registry, make sure `Docker` (with `Docker Compose` support) is installed and running. For a custom registry, make sure to run `docker login` in case authentication is needed.

```bash
docker compose up -d registry
```

### 2. ✨ Setting up a local cluster

#### 1. ✨ Minikube

Make sure that `Minikube` accepts the registry as well and has enough memory (configure docker before). In case you already have created a minikube cluster before you will have to recreated it in order to allow insecure registries, so delete it before creeating the new one. Use this command to create a new minikube cluster:

```bash
minikube start --cni=flannel --insecure-registry "host.internal:6789" --cpus 8 --memory 12000
```

Also add an additional node to allow running the loadgenerator (which can not run on the same node as the experiment itself):

```bash
minikube node add
```

In a multi-node setting, not all nodes might have the option to measure using scaphandre, so Clue ensures that only appropiate nodes are assigned with experiment pods. To simulate this for, e.g., the minikube node, you must apply a label:

```bash
kubectl label nodes minikube scaphandre=true
```

Lastly we need to manually flatten the kube config as minikube uses external files we can read from inside the containers. From clues base folder do the follwing:

```bash
cd localClusterConfig/minikube
./exportKubeConfig.sh
```

Afterwards open the docker-compose.yml and change the moundted volumes to use the just created config for the clue-deployer, so it should change it to this:

```yml
    volumes:
      # - ~/.kube:/root/.kube:ro
      # use this line if you want to use minikube - make sure to run the sh script first and commend out the line above
      - ./localClusterConfig/minikube/minikube_kube_config:/root/.kube/config:ro
```

#### 2. ✨ Kind

You can also use kind for running a local cluster, just use the provided config file to allow usage of the local registry and create the required nodes. Create your cluster like this:

```bash
kind create cluster --config ./localClusterConfig/kind/kind-config.yaml
```


### 3. 🛠️ CLUE2 setup

As the PSC tracker repository is private, clone it into `clue_deployer/agent` (uv is configured in the toml to find it there):

```bash
git clone https://github.com/ISE-TU-Berlin/PSC.git clue_deployer/agent
```

### 3. 🧱 Build Images for SUT (optional if existing)

Before running CLUE2, all images of the selected SUT have to be built and stored in the specified image registry. The image registry path `docker_registry_address` can be changed in the main config (by default, CLUE uses the registry deployed in previous steps).

To build images for the `TeaStore`, use the command listed below. By default the script builds images for all experiments.

```bash
docker compose up -d --build teastore-builder
```

To specify a single experiment you can modify the docker-compoye.yml file.

### 4. 🧪 SUT Test Deployment

For a test deployment of the SUT (without running the CLUE2, nor the workload generator), run the following command. Make sure that all required images are present in the specified image registry.

```bash
docker compose up -d --build teastore-deployer
```
You can adjust the deployment to your needs via the environment variables inside the docker-compoye.yml where `SUT` is the name of the SUT config inside of the `sut_configs` directory, and the `EXPERIMENT` is the name of the branch containing the desired experiment.

If you are deploying the Teastore locally you can forward a port so you to test and access the TeaStore:

```bash
kubectl port-forward service/teastore-webui 8080:80 --namespace=tea-bench
```

TeaStore may run some initial tasks on startup, so make sure to wait a minute if is slow / unavailable.

![TeaStore in the Browser](readme/teastore_jvm.png)

### 5. 💨 CLUE2 Deployment

To run the main CLUE2, run the task below. Make sure that all required images are present in the specified image registry.

```bash
python clue_deployer/main.py
```

![Running the Experiments](readme/running_experiments.png)

### 6. 📋 (Optional) CLUE2 Deployment with local 

If you create your own variants or make changes to the SUT, the images need to be rebuilt and pushed to the image registry specified in the config. Make sure to run `docker login` in case authentication is needed.

If all the preliminaries for data collection are installed, Clue will fetch the relevant measuremens from Prometheus and save them into the data folder. For data analysis, we provide Python notebooks seperately.

## 💻 Troubleshooting / Known Issues

 * When using docker desktop, enable in settings > advanced: *Allow the default Docker socket to be used*
 * Ensure that you have a sufficient amount of memory alocated for docker, at least 12 GB
 * Run `minikube dashboard` to monitor deployment errors, e.g. missing node labels or insufficient memory
 * The monolith app has some specific handles, e.g. a different set name. If a a set is not found, especially when skipping builds, this can cause probelems