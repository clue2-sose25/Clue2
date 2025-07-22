<div align="center">
  <h1 style="padding:15px;border-bottom: 0;">CLUE: Cloud-native Sustainability Evaluator</h1>
</div>

## 📢 About the Project

Clue is a benchmarking and observability framework for gathering and compiling sustainability and quality reports on changes in cloud-native applications.

It can be used as part of your CI/CD pipeline to evaluate the impact of changes or as a standalone tool to evaluate prototypes you are working on.

The framework is designed to be extensible and can be easily integrated with existing systems, relying on Prometheus to collect all relevant metrics. Moreover, we are currently focusing on Kubernetes as the orchestrator, so as long as your application runs on Kubernetes (Helm chart deployment), you can use Clue to evaluate it.

## 📦 Prerequisites

- Docker, e.g. 20.10
- Kubernetes Cluster, e.g. 1.29 (for local testing purposes: [kind](https://kind.sigs.k8s.io/), e.g. 0.29.0), with:
  - a linux based cluster, with at least two nodes running [Kepler](https://sustainable-computing.io/installation/kepler-helm/), a [NodeExporter](https://observability.thomasriley.co.uk/monitoring-kubernetes/metrics/node-exporter/), and [Prometheus](https://prometheus.io/) stack installed. If the tracker does not find any energy data, the experiment will start, but not generate any meaningful metrics.
  - for the serverless variants, `knative` installed
  - for additional external power readings, connect e.g. a Tapo device (out of scope of this Readme, read the [CLUE scientific paper](https://ieeexplore.ieee.org/abstract/document/10978924/))

## 🚀 System setup

> [!CAUTION]
> Please note that this repository also contains work in progress parts -- not all CLUE features and experiment branches that are not mentioned in the paper might be thoroughly tested.

In order to allow the usage of the CLUE2 in specific use cases, we offer a wide range of ways to deploy CLUE, depending on your needs and environment:

### 💻 CLUE2 Service + Web UI

The easiest and recommended way to deploy CLUE on your local machine is to interact with our custom Web UI.</br>
To deploy all necessary CLUE2 containers use:

```bash
docker compose up -d --build
```

CLUE Web UI should be available on the [localhost:5001](http://localhost:5001). Before running experiments, please read the rest of README.

The UI container serves the built files via **Nginx**. When running in a cluster you may need to configure the DNS resolver so Nginx can reach the deployer service. This is done with the environment variables `NGINX_RESOLVER` and `NGINX_RESOLVER_VALID`. The base URL of the API can be customised with `API_BASE_URL`.

### ⛓️ CLUE2 CLI

For headless deployment of CLUE2, we support deploying it as a standalone docker container. To configure it, edit the `.env` file:

```env
DEPLOY_AS_SERVICE=false
SUT=<sut_name>
VARIANTS=<variants>
WORKLOADS=<workloads>
N_ITERATIONS=<iterations>
```

Where the `<sut_name>` being the name of the SUT configuration file in the `sut_configs` directory, e.g. `teastore.yaml`.
</br> The `<variants>` should be a comma-separated list of variant names defined in the SUT configuration file, e.g. `baseline,serverless`.
</br> The `<workloads>` should be a comma-separated list of workload names defined in the SUT configuration file, e.g. `shaped,fixed`.
</br> The `<iterations>` is the number of iterations to run for each workload.

Before running the CLI command, make sure to read the rest of the README, while CLUE will immediately start the experiments. CLUE2 can then be run with the following command:

```bash
docker compose up --build clue-deployer
```

For a test deployment of the SUT, without running the benchmark itself, change the `DEPLOY_ONLY` value to `true`. Some SUT may run some initial tasks on the startup, so before accessing the SUT, make sure to wait a minute to compensate for slow / unavailable SUTs.

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

A sample kubeconfig is provided at `.github/actions/mock-kubeconfig.yaml`. Finally, encode the file and store the result as the `KUBECONFIG_B64` GitHub secret:

```bash
base64 -w0 .github/actions/mock-kubeconfig.yaml
```

## ✨ Cluster preparation

The SUT deployment and experiment will happen at the selected K8s cluster of choice. For local testing we recommend using `kind` cluster, however any cluster with following requirements should work:

- `Prometheus Node Exporter` - we recommend the Kube Prometheus Stack helm chart, which includes e.g. Node Exporter and Grafana resources.
- `Kepler` - we recommend to deploy the official `Kepler Helm chart` by following the official [Kepler docs](https://sustainable-computing.io/installation/kepler-helm/). If the `Prometheus Node Exporter` was setup before, one can skip the corresponding steps in the `Kepler` guide.

The cluster's kubeconfig can be provided in multiple ways. By default `docker-compose` mounts `~/.kube/config` into the deployer container. Alternatively you can set `KUBECONFIG_FILE` to mount a different file or pass a base64 encoded configuration via the `KUBE_CONFIG` environment variable (useful for CI environments).

If `DEPLOY_AS_SERVICE` is enabled and no kubeconfig is provided, the backend starts without a cluster connection. You can then upload the configuration from the Web UI at `/cluster`. The local cluster patching can be disabled by setting `PATCH_LOCAL_CLUSTER=false`.

For clusters that are only reachable via a SSH tunnel, you can specify a proxy command, that is executed after the kubeconfig has been patched. Define `CLUSTER_PROXY_COMMAND` in your `.env` and mount the required SSH key via `SSH_KEY_FILE`. For example:

```bash
CLUSTER_PROXY_COMMAND="ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no -N -L 6443:remote-cluster:6443 user@bastion"
SSH_KEY_FILE=~/.ssh/id_rsa
```

The entrypoint ensures the key permissions are correct and starts the command in the background before the deployer connects to the cluster.

### Using local `Kind` cluster

For local testing, we recommend using a `Kind` cluster, simply deployable by providing a config file. The cluster is configured to allow the usage of the local unsecure registry and to deploy the required number of nodes (at least 2) with designated node labels. Additionally, all created containers will be added to a custom `clue2` docker network. Deploy the pre-configured cluster using:

```bash
sh create-kind-cluster.sh
```

### Using remote cluster

When the `clue-deployer` is executed as a Pod in the same Kubernetes cluster, it automatically detects this by checking the `KUBERNETES_SERVICE_HOST` environment variable. In this case the in-cluster configuration is used and the `prepare_kubeconfig.py` step is skipped. Make sure the Pod runs with a `ServiceAccount` that has permissions to list and patch nodes and manage pods. `KUBERNETES_SERVICE_HOST` is automatically defined by Kubernetes for every container in the cluster, so you typically do not need to set it manually. An example RBAC manifest is provided in `clue_deployer/k8s/clue-deployer-rbac.yaml`. The local-cluster patching logic is disabled automatically when running in-cluster.

When running CLUE **outside** the cluster (for example via Docker Compose, but still deploying the experiments within the cluster) a kubeconfig must be supplied to the deployer. The container will patch the local cluster when `PATCH_LOCAL_CLUSTER=true` so the SUT images can be pulled from your registry.

To launch the deployer as a Kubernetes `Job`, apply the RBAC manifest and the provided example job file:

```bash
kubectl apply -f clue_deployer/k8s/clue-deployer-rbac.yaml
kubectl apply -f clue_deployer/k8s/clue-deployer-job.yaml
```

The job uses the `clue-deployer` ServiceAccount and stores results in a mounted volume. Adjust the `VARIANTS` and `WORKLOADS` variables in the manifest to suit your experiment.

## 🧪 Adding a new SUT support

To add a new SUT (System Under Test), follow these steps:

1. **Create a new SUT configuration file** in the `sut_configs` directory. Use an existing SUT as a template (we recommend teastore or toystore). It should be called `<sut_name>.yaml`.
2. **Define the SUT's variants** in the `variants` section of the configuration file. Each variant should have a unique name and specify the brach of the Git repository containing the code for the SUT.
3. **Build your images** and push them to the Docker registry specified in the `clue-config.yaml` file. You can use the local docker registry provided by CLUE or any other public/private registry. All required images for any given variant should be available in the specified Docker registry (including the workload generator described below), tagged by the selected `variant_name`.
4. **Deploy Clue** with the new SUT configuration. You can use any of the options specified in the `System setup` section.

### 🏁 Image registry

For the deployment of the SUT, CLUE connects to the provided docker image registry, specified in the `clue-config.yaml` file (`docker_registry_address`). CLUE expects all of the container images used by the SUTs to be present in the selected registry, including the workload generator image. Finally, the tags for the images should match the name of the currently deployed variant.

By default, CLUE deploys its own unsecure, local docker registry. To use any custom public or private registry, change the `clue-config.yaml` or visit the `Settings` page in our Web UI. Make sure CLUE will be able to access the images, by running `docker login` in case where authentication is needed.

### 🧱 Building the image for the clue loadgenerator

CLUE uses the `clue_loadgenerator` image to execute Locust workloads. The deployer orchestrates this through the `workload_runner.py` module. When a variant sets `colocated_workload: true`, the image is launched as a pod inside the cluster; otherwise the workload runs locally next to the deployer. As Clue comes with an integrated loadgenerator and developer just have to bring their config + locustfiles along with their SUT, it is required to once build the image for it and push it in the image registry.

```bash
docker compose up -d clue-loadgenerator-builder
```

When deploying with the Helm chart, the builder container is not used directly. Ensure the load generator image produced by this step is pushed to the registry referenced in `values.yaml` so the cluster can pull it.

Within a remote cluster, the Locust files listed in `workloads[*].locust_files` are packed into ConfigMaps and mounted into the container so you can customise your workload scripts without rebuilding the image.

### 🧱 (Optional) Build Images for the selected SUT

This step will differ based on the selected SUT. We provide a support for several SUTs listed in the `sut_configs` folder. Before running the CLUE deployer, all images of the selected SUT have to be built and stored in the specified image registry. The image registry path `docker_registry_address` can be changed in the main config (by default, CLUE uses the registry deployed in previous steps).

To build images for the selected SUT, use one of the commands listed below.

- [Teastore](https://github.com/ISE-TU-Berlin/sustainable_teastore)

  ```bash
  docker compose up -d --build teastore-builder
  ```

  By default the script builds images for all experiments. To specify a single experiment you can modify the `.env` file and change the `TEASTORE_EXP_NAME` environment variable to contain the name of one of the experiments listed in the `sut_configs/teastore.yaml` file.

- [Open Telemetry Shop](https://github.com/clue2-sose25/opentelemetry-demo)

  ```bash
  docker compose up -d --build ots-builder
  ```

- [Toystore](https://github.com/clue2-sose25/sustainable_toystore) (a custom, simple SUT created for CLUE2)

  ```bash
  docker compose up -d --build toystore-builder
  ```

Wait for the selected builder to be finished, indicated by its container showing a status `Exited`. To check if the images have been successfully stored in the registry, visit the `http://localhost:9000/v2/_catalog` page.

### Helm deployment

A basic Helm chart is provided under `clue_helm/` to run the deployer and web UI directly in a cluster.
Install it with (e.g. using `ToyStore` values file):

```bash
helm upgrade --install clue clue_helm --namespace clue --create-namespace -f clue_helm/values-toystore.yaml
```

Set `imageRegistry` and other values in `values.yaml` to point to your images and configure the ingress host.
The chart deploys all CLUE components into the `clue` // Release.Namespace. SUT deployments are created in a separate namespace defined in the SUT config on nodes labeled `scaphandre=true`.

Running with the Helm chart means both the deployer and web UI operate **inside
the cluster**. The container automatically detects this via the
`KUBERNETES_SERVICE_HOST` variable and skips the kubeconfig preparation. When you
run CLUE via Docker Compose or the CLI outside the cluster, make sure to provide
a kubeconfig (see `PATCH_LOCAL_CLUSTER` description above).

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
to mount a folder of Locust scripts, pass its location via the `values.yaml`
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
through the GitHub action's `values.yaml` input. The action mounts the folder into the chart and
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

# 2. Run CLUE experiment (observability stack is automatically set up)
docker compose up -d --build clue-deployer

# 3. Access Grafana automatically at http://localhost:30080 (admin/prom-operator)
```

**Perfect for:**

- Production environments
- Multi-node clusters
- Running CLUE experiments
- Fully automated observability setup
- Enterprise deployments

## Fully Integrated Observability Stack

CLUE now provides **complete automation** of the observability stack setup during experiment deployment:

### ✨ **Automated Features:**

- **🚀 Prometheus + Grafana installation** via Helm charts during CLUE deployment
- **📊 Kepler energy monitoring** automatic installation and configuration
- **🎯 Dashboard provisioning** - Kepler sustainability dashboard automatically available
- **🔧 Service configuration** - NodePort services (30080, 30090) ready immediately
- **✅ Health validation** - all components tested and verified during setup

### 🎯 **Zero Manual Setup Required!**

When you run CLUE experiments, the observability stack is automatically configured as part of the deployment process. Simply run:

```bash
docker compose up -d --build clue-deployer
```

And access your dashboards immediately at **http://localhost:30080** (admin/prom-operator)

### Configuration Management

CLUE uses centralized configuration for all observability components. The Prometheus URL is defined in `clue-config.yaml` and used consistently across all components:

```yaml
prometheus_url: "http://clue-cluster-control-plane:30090"
```

### Accessing the Grafana Dashboard

After successful deployment, you can access Grafana at:

- URL: `http://localhost:30080` (or your configured port)
- Username: `admin` (or your configured username)
- Password: `prom-operator` (or your configured password)

The Kepler dashboard will be automatically imported and available in the Grafana interface, showing real-time sustainability metrics including energy consumption, carbon emissions, and resource utilization.
