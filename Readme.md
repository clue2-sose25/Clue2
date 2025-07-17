<div align="center">
  <h1 style="padding:15px;border-bottom: 0;">CLUE: Cloud-native Sustainability Evaluator</h1>
</div>

## 📢 About the Project

Clue is a benchmarking and observability framework for gathering and compiling sustainability and quality reports on changes in cloud-native applications.

It can be used as part of your CI/CD pipeline to evaluate the impact of changes or as a standalone tool to evaluate prototypes you are working on.

The framework is designed to be extensible and can be easily integrated with existing systems. We currently rely on Prometheus to collect all relevant metrics, but we are working on adding support for other monitoring tools. Moreover, we are currently focusing on Kubernetes as the orchestrator, so as long as your application runs on Kubernetes, you can use Clue to evaluate it. However, we are working on adding support for other environments as well.

## 📦 Prerequisites

- Docker, e.g. 20.10
- Kubernetes Cluster, e.g. 1.29 (for local testing purposes: [kind](https://kind.sigs.k8s.io/), e.g. 0.29.0), with:
  - at least one node running [Kepler](https://sustainable-computing.io/installation/kepler-helm/), and a [NodeExporter](https://observability.thomasriley.co.uk/monitoring-kubernetes/metrics/node-exporter/). If the tracker does not find any energy data, the experiment will start, but not generate any meaningful metrics.
  - for the serverless variant, `knative` installed
  - for external power meters, connect e.g. a Tapo device (out of scope of this Readme, read the [CLUE scientific paper](https://ieeexplore.ieee.org/abstract/document/10978924/))

## 🚀 System setup

> [!CAUTION]
> Please note that this repository also contains work in progress parts -- not all CLUE features and experiment branches that are not mentioned in the paper might be thoroughly tested.

For specific use cases, we offer a wide range of ways to deploy CLUE.

### 💻 CLUE Web UI

The easiest and recommended way to deploy CLUE on your local machine is to interact with our custom Web UI. To deploy all necessary CLUE container use:

```bash
docker compose up -d --build
```

CLUE Web UI should be available on the [localhost:5001](http://localhost:5001). Before running experiments, make sure to read the `CLUE Components` section.

### ⛓️ CLUE CLI

For headless deployment of CLUE we support deploying CLUE as a standalone deployer docker container.

Before running the CLI command, make sure to read the `CLUE Components` section, while CLUE will immediatelly start the experiments.

### 📦 CLUE GitHub Integration

CLUE can also be easily integrated to any existing GitHub CI-CD Pipeline, taking use of our public `clue-deployer` action.
To successfully run CLUE action, several parameters need to be provided, including the cluster config.
All collected metrics to the directory specified by the `results-path` input and uploads those files as an artifact called
`clue-results`.

The artifact is available for download from the Actions UI or it can be fetched in later jobs with `actions/download-artifact`.

```yaml
jobs:
  run-clue:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: clue2-sose25/Clue2/.github/actions/clue-deployer@latest
        with:
          clue-config-path: ./clue/clue-config.yaml
          sut-config-path: ./clue/toystore-config.yaml
          image-registry: ghcr.io/clue2-sose25/sustainable_toystore
          variants-name: main
          results-path: clue_results
          kubeconfig: ${{ secrets.KUBECONFIG_B64 }}
          patch-local-cluster: "true"
```

A sample kubeconfig is provided at `.github/actions/mock-kubeconfig.yaml`. Encode the file and store the result as the `KUBECONFIG_B64` GitHub secret:

```bash
base64 -w0 .github/actions/mock-kubeconfig.yaml
```

## CLUE Components

With CLUE being a highly modular system, all of its components can be configured for the specific use case.

### 🏁 Image registry

For the deployment of the SUT, CLUE connects to the provided docker image registry, specified in the `clue-config.yaml` file (`docker_registry_address`). CLUE expects all of the container images used by the SUTs to be present in the selected registry, including the workload generator image. Finally, the tags for the images should match the name of the currently deployed variant.

By default, CLUE deploys its own unsecure, local docker registry. To use any custom public or private registry change the `clue-config.yaml` or visit the `Settings` page in our Web UI. Make sure CLUE will be able to access the images, by running `docker login` in case where authentication is needed.

### ✨ Cluster preparation

The SUT deployment and experiment will happen at the selected K8s cluster of choice. For local testing we recommend using `kind` cluster, however any cluster with following requirements should work:

- `Prometheus Node Exporter` - we recommend the Kube Prometheus Stack helm chart, which includes e.g. Node Exporter and Grafana resources.
- `Kepler` - we recommend to deploy the official `Kepler Helm chart` by following the official [Kepler docs](https://sustainable-computing.io/installation/kepler-helm/). If the `Prometheus Node Exporter` was setup before, one can skip the corresponding steps in the `Kepler` guide.

The cluster's kubeconfig can be provided in multiple ways. By default `docker-compose` mounts `~/.kube/config` into the deployer container. Alternatively you can set `KUBECONFIG_FILE` to mount a different file or pass a base64 encoded configuration via the `KUBE_CONFIG` environment variable (useful for CI environments).

If `DEPLOY_AS_SERVICE` is enabled and no kubeconfig is provided, the backend starts without a cluster connection. You can then upload the configuration from the Web UI at `/cluster`. The local cluster patching can be disabled by setting `PATCH_LOCAL_CLUSTER=false`.

For clusters that are only reachable via a bastion host ( Jump Host ) you can specify a proxy command that is executed after the kubeconfig has been patched. Define `CLUSTER_PROXY_COMMAND` in your `.env` and mount the required SSH key via `SSH_KEY_FILE`:

```bash
CLUSTER_PROXY_COMMAND="ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no -N -L 6443:remote-cluster:6443 user@bastion"
SSH_KEY_FILE=~/.ssh/id_rsa
```

The entrypoint ensures the key permissions are correct and starts the command in the background before the deployer connects to the cluster.

### Running inside the cluster

When the `clue-deployer` is executed as a Pod in the same Kubernetes cluster, it
automatically detects this by checking the `KUBERNETES_SERVICE_HOST` environment
variable. In this case the in-cluster configuration is used and the
`prepare_kubeconfig.py` step is skipped. Make sure the Pod runs with a
`ServiceAccount` that has permissions to list and patch nodes and manage pods.
`KUBERNETES_SERVICE_HOST` is automatically defined by Kubernetes for every
container in the cluster, so you typically do not need to set it manually.
An example RBAC manifest is provided in `clue_deployer/k8s/clue-deployer-rbac.yaml`.
The local-cluster patching logic is disabled automatically when running in-cluster.

To launch the deployer as a Kubernetes `Job`, apply the RBAC manifest and the
provided example job file:

```bash
kubectl apply -f clue_deployer/k8s/clue-deployer-rbac.yaml
kubectl apply -f clue_deployer/k8s/clue-deployer-job.yaml
```

The job uses the `clue-deployer` ServiceAccount and stores results in a mounted
volume. Adjust the `VARIANTS` and `WORKLOADS` variables in the manifest to suit
your experiment.

1. Setting up a local `Kind` cluster

For local testing, we recommend using a `Kind` cluster, simply deployable by providing a config file. The cluster is configured to allow the usage of the local unsecure registry and to deploy the required number of nodes (at least 2) with designated node labels. Additionally, all created containers will be added to a custom `clue2` docker network. Deploy the pre-configured cluster using:

```bash
sh create-kind-cluster.sh
```

### 🧱 Built the image for the clue loadgenerator

As Clue comes with an integrated loadgenerator and developer just have to bring their config + locustfiles along with their SUT, it is required to once build the image for it and push it in the image registry.

```bash
docker compose up -d clue-loadgenerator-builder
```

### 🧱 (Optional) Build Images for the selected SUT

This step will differ based on the selected SUT. We provide a support for several SUTs listed in the `sut_configs` folder. Before running the CLUE deployer, all images of the selected SUT have to be built and stored in the specified image registry. The image registry path `docker_registry_address` can be changed in the main config (by default, CLUE uses the registry deployed in previous steps).

To build images for the selected SUT, use one of the commands listed below.

- Teastore

  ```bash
  docker compose up -d --build teastore-builder
  ```

  By default the script builds images for all experiments. To specify a single experiment you can modify the `.env` file and change the `TEASTORE_EXP_NAME` environment variable to contain the name of one of the experiments listed in the `sut_configs/teastore.yaml` file.

- Open Telemetry Shop

  ```bash
  docker compose up -d --build ots-builder
  ```

- Toystore (custom, simple SUT)

  ```bash
  docker compose up -d --build toystore-builder
  ```

Wait for the selected builder to be finished, indicated by its container showing a status `Exited`. To check if the images have been successfully stored in the registry, visit the `http://localhost:9000/v2/_catalog` page.

### Load Generator & Locust

CLUE uses the `clue_loadgenerator` image to execute Locust workloads. The deployer orchestrates this through the `workload_runner.py` module. When a variant sets `colocated_workload: true`, the image is launched as a pod inside the cluster; otherwise the workload runs locally next to the deployer.

For the deployment outside the K8s Cluster, Build the image once before running experiments:

```bash
docker compose up -d clue-loadgenerator-builder
```

The Locust files listed in `workloads[*].locust_files` are packed into ConfigMaps and mounted into the container so you can customise your workload scripts without rebuilding the image.

### 🧪 SUT Test Deployment (without running the benchmark)

For a test deployment of the SUT, without running the benchmark itself, open the `.env` file and change the `DEPLOY_ONLY` value to `true`. Make sure that all required images are present in the specified image registry. Next, run the deployer:

```bash
docker compose up -d --build clue-deployer
```

You can adjust the deployment to your needs via the environment variables inside the `.env` file, where `SUT` is the name of the SUT config inside of the `sut_configs` directory, and the `VARIANTS` is the name of the branch containing the desired experiment.

If you are deploying the Teastore locally you can forward a port so you to test and access the TeaStore:

```bash
kubectl port-forward service/teastore-webui 8080:80 --namespace=tea-bench
```

Some SUT may run some initial tasks on the startup, so before accessing the SUT, make sure to wait a minute to compensate for slow / unavailable SUTs.

### 💨 CLUE2 Deployment

To run the main CLUE2, run the task below. Make sure that all required images are present in the specified image registry.

```bash
docker compose up -d --build clue-deployer
```

![Running the Experiments](public/running_experiments.png)

### 📋 (Optional) CLUE2 Deployment with local changes

If you create your own variants or make changes to the SUT, the images need to be rebuilt and pushed to the image registry specified in the config. Make sure to run `docker login` in case authentication is needed.

If all the preliminaries for data collection are installed, Clue will fetch the relevant measuremens from Prometheus and save them into the data folder. For data analysis, we provide Python notebooks seperately.

### 💻 Troubleshooting / Known Issues

- When using docker desktop, enable in settings > advanced: _Allow the default Docker socket to be used_
- Ensure that you have a sufficient amount of memory alocated for docker, at least 12 GB
- Run `minikube dashboard` to monitor deployment errors, e.g. missing node labels or insufficient memory
- The monolith app has some specific handles, e.g. a different set name. If a a set is not found, especially when skipping builds, this can cause problems.

### Helm deployment

A basic Helm chart is provided under `clue_helm/` to run the deployer and web UI directly in a cluster.
Install it with (e.g. using `ToyStore` values file):

```bash
helm upgrade --install clue clue_helm --namespace clue --create-namespace -f clue_helm/values-toystore.yaml
```

Set `imageRegistry` and other values in `values.yaml` to point to your images and configure the ingress host.
The chart deploys all CLUE components into the `clue` // Release.Namespace. SUT deployments are created in a separate namespace defined in the SUT config on nodes labeled `scaphandre=true`.

The chart includes a `Job` manifest for CI execution and a `Deployment` for a long-running service. A second job `clue-loadgenerator` can be used to run Locust in the cluster next to the deployer. Locust scripts are taken from the ConfigMap `loadgenerator-workload`, created from entries in `loadGenerator.workloadFiles` in the values file and mounted under `sut_configs/workloads/<sut>/`.

For automated tests you can use the composite action under
`.github/actions/helm-deploy` which deploys the chart when a
base64 encoded kubeconfig is supplied via the `kubeconfig` input. Optional
`namespace` and `values-file` inputs allow you to specify the target namespace
and an override file for the chart. See the workflow
`.github/workflows/clue-deployer-helm.yml` for an example.
The repository includes `clue_helm/values-toystore.yaml` which sets the
environment variables to run the `toystore` SUT with the `baseline` variant.
An additional template `clue_helm/values-example.yaml` shows all required fields.
Copy this file to your own repository and adjust the registry and tags. Provide the
path via the `values-file` input of the action to deploy your SUT. When you need
to mount a folder of Locust scripts, pass its location via the `workload-folder`
input. The action copies that folder next to the chart and sets
`loadGenerator.workloadDir` accordingly.
If the chart is stored in a registry, supply its reference via the
`chart-ref` input. Otherwise the action uses the `chart-path` (default
`clue_helm`) to deploy a local copy.
From this version on the deployer expects the selected SUT configuration file to be
available under `/app/sut_configs/`. Supply the YAML content via the `sutConfig`
value (and optional `sutConfigFileName`) so the chart can create a `sut-config`
ConfigMap and mount it into both the `Deployment` and `Job`.
The main CLUE configuration is also required at `/app/clue-config.yaml`. Provide
its YAML via the `clueConfig` value so a `clue-config-file` ConfigMap gets mounted
to that path.
See `clue_helm/values-toystore.yaml` for an example embedding the configuration and
the workflow `.github/workflows/clue_deploy_toystore_helm.yml` for usage of the
Helm action.

#### Locust workload deployment

`workload_runner.py` uses the `clue_loadgenerator` image to run Locust. For each path
listed under `workloads[*].locust_files` in the SUT configuration a ConfigMap is
created which contains the file content. Those ConfigMaps are mounted at
`/app/locustfiles` in the load generator pod and referenced by the `LOCUST_FILE`
environment variable. If the selected variant has `colocated_workload: true`,
the pod runs inside the cluster. Otherwise the load generator container is
executed locally next to the deployer.
When deploying via Helm you can supply one or multiple scripts through `loadGenerator.workloadFiles`.
The chart mounts them at `sut_configs/workloads/<sut>/` and sets `LOCUST_FILE` to a comma separated list of their paths
before launching the `clue-loadgenerator` job.
Alternatively you can put your Locust scripts in a folder and reference it via `loadGenerator.workloadDir`.
All files in that folder become entries in the `loadgenerator-workload` ConfigMap. This is convenient
when invoking the Helm chart from another repository: copy the folder next to the chart and pass its path
through the GitHub action's `workload-folder` input. The action mounts the folder into the chart and
sets `loadGenerator.workloadDir` automatically.

## 🚀 Observability Stack Setup: Two Options

CLUE provides two main approaches for setting up the observability stack with Grafana dashboards:

### Option 1: Docker Compose Setup (Recommended for Local Development)

The simplest way to get started with Grafana and energy monitoring:

```bash
# Start the complete observability stack
docker compose up -d

# Access Grafana immediately
# Open: http://localhost:3000 (admin/prom-operator)
```

**Perfect for:**

- Local development and testing
- Quick prototyping
- Learning and experimentation
- CI/CD environments

### Option 2: Kubernetes Setup (For Production/Cluster Environments)

For full Kubernetes deployments with the CLUE experiment framework:

```bash
# 1. Create Kind cluster
./create-kind-cluster.sh

# 2. Automated setup (installs Prometheus, Kepler, Grafana + imports dashboard)
python setup_observability.py

# 3. Access Grafana
kubectl port-forward -n default service/kps1-grafana 3000:80
# Open: http://localhost:3000 (admin/prom-operator)
```

**Perfect for:**

- Production environments
- Multi-node clusters
- Running CLUE experiments
- Enterprise deployments

## Automated Grafana Dashboard Setup

CLUE now automatically handles the complete observability stack setup, including:

- **Automated Prometheus and Kepler installation** via Helm charts
- **Grafana dashboard import** - automatically imports the Kepler sustainability dashboard
- **Service configuration** - sets up NodePort services for easy access
- **Health validation** - ensures all components are working correctly

The observability stack is automatically configured during the experiment deployment phase. No manual setup is required!

### Configuration Management

CLUE uses centralized configuration for all observability components. The Prometheus URL is defined in `clue-config.yaml` and used consistently across all components:

```yaml
prometheus_url: "http://clue-cluster-control-plane:30090"
```

To update Grafana provisioning to match your current CLUE configuration:

```bash
# Update Grafana datasource configuration based on CLUE config
python update_grafana_config.py
```

This script dynamically updates the Grafana provisioning files to use the correct Prometheus URL from your CLUE configuration.

### Accessing the Grafana Dashboard

After successful deployment, you can access Grafana at:

- URL: `http://localhost:30080` (or your configured port)
- Username: `admin` (or your configured username)
- Password: `prom-operator` (or your configured password)

The Kepler dashboard will be automatically imported and available in the Grafana interface, showing real-time sustainability metrics including energy consumption, carbon emissions, and resource utilization.
