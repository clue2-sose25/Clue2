<div align="center">
  <h1 style="padding:15px;border-bottom: 0;">CLUE: Cloud-Native Sustainability Evaluator</h1>
</div>

## 📢 About the Project

CLUE is a benchmarking and observability framework designed to gather and compile sustainability and quality reports for cloud-native applications. It enables the evaluation of changes by integrating seamlessly into your CI/CD pipeline or functioning as a standalone tool for assessing prototypes.

The framework is extensible and integrates effortlessly with existing systems, leveraging Prometheus for comprehensive metrics collection. Currently, CLUE focuses on Kubernetes as the orchestrator. As long as your application operates on Kubernetes (via Helm chart deployment), CLUE can evaluate its performance and sustainability.

## 📦 Prerequisites

- **Docker** (e.g., version 20.10 or later)
- **Kubernetes Cluster** (e.g., version 1.29 or later). For local testing, we recommend [kind](https://kind.sigs.k8s.io/) (e.g., version 0.29.0 or later). The cluster must include:
  - A Linux-based cluster with at least two nodes, equipped with:
    - [Kepler](https://sustainable-computing.io/installation/kepler-helm/) for energy monitoring
    - [NodeExporter](https://observability.thomasriley.co.uk/monitoring-kubernetes/metrics/node-exporter/) for node metrics
    - [Prometheus](https://prometheus.io/) for metrics collection and storage  
      _Note:_ If Kepler detects no energy data, experiments will proceed but won’t yield meaningful sustainability metrics.
  - For serverless variants: [Knative](https://knative.dev/) installed on the cluster
  - For additional external power readings: Connect a device such as a Tapo smart plug (outside the scope of this README; refer to the [CLUE scientific paper](https://ieeexplore.ieee.org/abstract/document/10978924/) for details)

## 🚀 System Setup

> [!CAUTION]  
> Please note that this repository includes work-in-progress components. Not all CLUE features or experiment branches mentioned in the paper have been fully tested.

To accommodate diverse use cases, CLUE2 offers multiple deployment options tailored to your specific needs and environment:

### 💻 CLUE2 Service + Web UI

The simplest and recommended method for deploying CLUE2 on your local machine is through our custom Web UI. To deploy all necessary CLUE2 containers, run:

```bash
docker compose up -d --build
```

The CLUE Web UI will be accessible at [http://localhost:5001](http://localhost:5001). Before running experiments, please review the remainder of this README.

The UI container serves built files using **Nginx**. When deployed in a cluster, you may need to configure the DNS resolver to enable Nginx to reach the deployer service. Use the environment variables `NGINX_RESOLVER` and `NGINX_RESOLVER_VALID` for this purpose. The API base URL can also be customized via `API_BASE_URL`.

### ⛓️ CLUE2 CLI

For headless deployment, CLUE2 can be run as a standalone Docker container. Configure it by editing the `.env` file:

```env
DEPLOY_AS_SERVICE=false
SUT=<sut_name>
VARIANTS=<variants>
WORKLOADS=<workloads>
N_ITERATIONS=<iterations>
```

- `<sut_name>`: The name of the SUT configuration file in the `sut_configs` directory (e.g., `teastore.yaml`)
- `<variants>`: A comma-separated list of variant names from the SUT configuration file (e.g., `baseline,serverless`)
- `<workloads>`: A comma-separated list of workload names from the SUT configuration file (e.g., `shaped,fixed`)
- `<iterations>`: The number of iterations to execute for each workload

CLUE2 deployer will initiate experiments immediately. Therefore, make sure other required services are already up and running. Recommended way to do it is to deploy CLUE2 as the `Service + Web UI` option listed above and then re-build and re-deploy the `CLUE deployer` using:

```bash
docker compose up --build clue-deployer
```

For a test deployment of the SUT without running the benchmark, set `DEPLOY_ONLY` to `true`. Some SUTs perform initial tasks at startup, so wait approximately one minute before accessing the SUT to account for delays or unavailability.

### 📦 CLUE GitHub Integration

CLUE seamlessly integrates into any GitHub CI/CD pipeline using our public action at `.github/actions/clue-helm/action.yaml`. CLUE GitHub action connects to the cluster provided via the base64-encoded kubeconfig and deploys CLUE2 pods in the provided namespace. Next, CLUE deployer reads the provided `values-<sut_name>.json` file and deploys & measures the selected SUT as K8s resources in the same cluster.

The resulting artifact can be downloaded from the Web UI or retrieved in subsequent jobs using `actions/download-artifact`.

For details on integration into any GitHub repository, refer to our custom SUT [ToyStore](https://github.com/clue2-sose25/sustainable_toystore) repository. For example values configuration, see `clue_helm/values-toystore.yaml`. Mentioned example deploys the `toystore` SUT with the `baseline` variant. To adapt it to your selected SUT:

1. Copy `values-toystore.yaml` to your repository and adjust its parameters as needed.
2. Extend your existing GitHub CI-CD pipeline with the above mentioned CLUE2 action, providing all necessary parameters (see example configuration).
3. Encode the kubeconfig file in base64 and store it as the `KUBECONFIG_B64` GitHub secret (see example config at `.github/actions/clue-deployer-outside-cluster/mock-kubeconfig.yaml`)

To include a folder of Locust scripts:

- Specify the folder’s location in `values.yaml`.
- The action copies the folder adjacent to the chart and sets `loadGenerator.workloadDir` accordingly.

If the chart is stored in a registry, provide its reference via `chart-ref`. Otherwise, the action uses `chart-path` (default: `clue_helm`) to deploy a local copy.

The deployer expects the SUT configuration file at `/app/sut_configs/`. Supply its YAML content via `sutConfig` (and optionally `sutConfigFileName`) to create a `sut-config` ConfigMap, mounted into both `Deployment` and `Job` resources. Similarly, provide the main CLUE configuration YAML via `clueConfig` for a `clue-config-file` ConfigMap, mounted at `/app/clue-config.yaml`.

## ✨ Cluster Preparation

The SUT deployment and experiments will occur on your chosen Kubernetes cluster. For local testing, we recommend a `kind` cluster, though any cluster meeting these requirements will suffice:

- **Prometheus Node Exporter**: Install via the Kube Prometheus Stack Helm chart, which includes Node Exporter and Grafana resources.
- **Kepler**: Deploy the official Kepler Helm chart per the [Kepler documentation](https://sustainable-computing.io/installation/kepler-helm/). Skip Node Exporter steps if already installed.

The cluster’s kubeconfig can be supplied as follows:

- By default, `docker-compose` mounts `~/.kube/config` into the deployer container.
- Set `KUBECONFIG_FILE` to mount a different file.
- Pass a base64-encoded configuration via `KUBE_CONFIG` (ideal for CI environments).

If `DEPLOY_AS_SERVICE` is enabled without a kubeconfig, the backend starts without a cluster connection. Upload the configuration via the Web UI at `/cluster`. Disable local cluster patching by setting `PATCH_LOCAL_CLUSTER=false`.

For clusters accessible only via an SSH tunnel, define a proxy command in `.env` with `CLUSTER_PROXY_COMMAND` and mount the SSH key via `SSH_KEY_FILE`. Example:

```bash
CLUSTER_PROXY_COMMAND="ssh -i /root/.ssh/id_rsa -o StrictHostKeyChecking=no -N -L 6443:remote-cluster:6443 user@bastion"
SSH_KEY_FILE=~/.ssh/id_rsa
```

The entrypoint script ensures correct SSH key permissions and runs the proxy command in the background before the deployer connects.

### Using Local `kind` Cluster

For local testing, deploy a `kind` cluster with a provided configuration file. It supports the local insecure registry, deploys at least two nodes with specific labels, and adds containers to a `clue2` Docker network. Deploy it with:

```bash
sh create-kind-cluster.sh
```

### Using Remote Cluster

When running `clue-deployer` as a Pod in the same Kubernetes cluster, it detects this via `KUBERNETES_SERVICE_HOST`. The in-cluster configuration is used, skipping `prepare_kubeconfig.py`. Ensure the Pod’s `ServiceAccount` has permissions to list/patch nodes and manage pods. An example RBAC manifest is at `clue_deployer/k8s/clue-deployer-rbac.yaml`. Local patching is disabled in-cluster.

When running CLUE **outside** the cluster (e.g., via Docker Compose) but deploying experiments within it, supply a kubeconfig. The container patches the cluster if `PATCH_LOCAL_CLUSTER=true` to pull SUT images.

To launch the deployer as a Kubernetes `Job`, apply:

```bash
kubectl apply -f clue_deployer/k8s/clue-deployer-rbac.yaml
kubectl apply -f clue_deployer/k8s/clue-deployer-job.yaml
```

Adjust `VARIANTS` and `WORKLOADS` in the manifest as needed.

#### Helm Deployment

A Helm chart at `clue_helm/` runs the deployer and Web UI in-cluster. Install it with (e.g., `ToyStore` values):

```bash
helm upgrade --install clue clue_helm --namespace clue --create-namespace -f clue_helm/values-toystore.yaml
```

Configure `imageRegistry` and other `values.yaml` settings for your images and ingress host. SUT deployments occur in a separate namespace on nodes labeled `scaphandre=true`.

The chart places the deployer and Web UI **inside the cluster**, including a `Job` for CI/CD, a `Deployment` for continuous operation, and a `clue-loadgenerator` Job for Locust. Scripts are sourced from the `loadgenerator-workload` ConfigMap, mounted at `sut_configs/workloads/<sut>/`.

#### Locust Workload Deployment

The `workload_runner.py` script uses `clue_loadgenerator` to run Locust. ConfigMaps created from `workloads[*].locust_files` are mounted at `/app/locustfiles`, referenced by `LOCUST_FILE`. If `colocated_workload: true`, the pod runs in-cluster; otherwise, it runs locally. Via Helm, supply scripts through `loadGenerator.workloadFiles` or a folder via `loadGenerator.workloadDir`, which populates the `loadgenerator-workload` ConfigMap.

## 🧪 Adding a New SUT

To integrate a new System Under Test (SUT):

1. **Create a Configuration File**: Place it in `sut_configs`, using `teastore.yaml` or `toystore.yaml` as a template. Name it `<sut_name>.yaml`.
2. **Define Variants**: In the `variants` section, assign unique names and specify the Git branch with the SUT code.
3. **Define workloads**: In the `workloads` section, define the possible workloads for the SUT, including the locust file names, used by the workload generator.
4. **Build and Push Images**: Build images and push them to the registry in `clue-config.yaml`. Tag them with the variant name.
5. **Deploy CLUE**: Use any method from the `System Setup` section.

### 🏁 Image Registry

CLUE connects to the registry at `docker_registry_address` in `clue-config.yaml`. All SUT images, including the workload generator, must be present and tagged with the variant name. By default, CLUE uses an insecure local registry. Update `clue-config.yaml` or the Web UI’s `Settings` page for a custom registry, ensuring access with `docker login` if authenticated.

### 🧱 Building the CLUE Load Generator Image

The `clue_loadgenerator` image runs Locust workloads via `workload_runner.py`. Build and push it with:

```bash
docker compose up -d clue-loadgenerator-builder
```

For Helm, push the image to the registry in `values.yaml`. Locust files are mounted via ConfigMaps in remote clusters.

### 🧱 (Optional) Build Images for the Selected SUT

Build SUT images based on the chosen SUT from `sut_configs`. Example commands:

- [**Teastore**](https://github.com/ISE-TU-Berlin/sustainable_teastore)

  ```bash
  docker compose up -d --build teastore-builder
  ```

  Modify `TEASTORE_EXP_NAME` in `.env` to build images for a specific variant.

- [**Open Telemetry Shop**](https://github.com/clue2-sose25/opentelemetry-demo)

  ```bash
  docker compose up -d --build ots-builder
  ```

  Modify `TOYSTORE_EXP_NAME` in `.env` to build images for a specific variant.

- [**Toystore**](https://github.com/clue2-sose25/sustainable_toystore) (a custom, simple SUT created for CLUE2)

  ```bash
  docker compose up -d --build toystore-builder
  ```

  Modify `OTS_EXP_NAME` in `.env` to build images for a specific variant.

Wait for the builder to exit, then verify images at `http://localhost:9000/v2/_catalog`.

## 🚀 CLUE2 Observability

CLUE2 centralizes observability configuration, with the Prometheus URL in `clue-config.yaml`, with default value for local `Kind` cluster:

```yaml
prometheus_url: "http://clue-cluster-control-plane:30090"
```

Two methods are offered for Grafana dashboards. Access Grafana post-deployment at:

- URL: `http://localhost:30080` (installed automatically inside the cluster) or `http://localhost:3000` (deployed within docker compose stack)
- Username: `admin`
- Password: `prom-operator`

The Kepler dashboard displays real-time sustainability metrics.
