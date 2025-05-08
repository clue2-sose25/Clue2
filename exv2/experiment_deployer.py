from os import path
import subprocess
import time
import kubernetes
import docker

from experiment import Experiment
from scaling_experiment_setting import ScalingExperimentSetting
from experiment_autoscaling import ExperimentAutoscaling

import logging

class ExperimentDeployer:

    def __init__(self, experiment: Experiment):
        self.experiment = experiment
        self.docker_client = docker.from_env()

    def build_images(self):
        """
        build all the images for the experiment and push them to the docker registry.

        perform some patching of the build scripts to use buildx (for multi-arch builds)
        """

        exp = self.experiment

        git = subprocess.check_call(
            ["git", "switch", exp.target_branch], cwd=path.join(exp.env.sut_path)
        )
        if git != 0:
            raise RuntimeError(f"failed to switch git to {exp.target_branch}")

        print(f"Using the `{exp.target_branch}` SUT branch")

        # ensure mvn build ...
        # docker run -v foo:/mnt --rm -it --workdir /mnt  maven mvn clean install -DskipTests
        # try: 

        print(f"Deploying the maven container. Might take a while...")
        mvn_output = self.docker_client.containers.run(
            image="maven",
            auto_remove=True,
            volumes={
                path.abspath(path.join(exp.env.sut_path)): {
                    "bind": "/mnt",
                    "mode": "rw",
                }
            },
            working_dir="/mnt",
            command="bash -c 'apt-get update && apt-get install -y dos2unix && find . -type f -name \"*.sh\" -exec dos2unix {} \\; && mvn clean install -DskipTests'",
        )
        if "BUILD SUCCESS" not in mvn_output.decode("utf-8"):
            print(mvn_output)
            raise RuntimeError(
                "failed to build teastore. Run mvn clean install -DskipTests manually and see why it fails"
            )
        else:
            print("Finished rebuiling java deps")

        # patch build_docker.sh to use buildx
        print(f"Patching the build_docker.sh")
        with open(
            path.join(exp.env.sut_path, "tools", "build_docker.sh"), "r"
        ) as f:
            script = f.read()

        if "buildx" in script:
            print("buildx already used")
        else:
            script = script.replace(
                "docker build",
                f"docker buildx build --platform {exp.env.remote_platform_arch}",
            )
            if exp.env.kind_cluster_name:
                script = script.replace(
                    "docker push",
                    f"kind load docker-image --name {exp.env.kind_cluster_name}",
                )
            with open(
                path.join(exp.env.sut_path, "tools", "build_docker.sh"), "w"
            ) as f:
                f.write(script)
            
        # 2. cd tools && ./build_docker.sh -r <env["docker_user"]/ -p && cd ..
        print(f"Running the build_docker.sh")
        build = subprocess.check_call(
            ["sh", "build_docker.sh", "-r", f"{exp.env.docker_registry_address}/", "-p"],
            cwd=path.join(exp.env.sut_path, "tools"),
        )

        if build != 0:
            raise RuntimeError(
                "failed to build docker images. Run build_docker.sh manually and see why it fails"
            )

        print(f"Finished building {exp.env.docker_registry_address}/* images")

    def deploy_branch(self, observations: str = "data/default"):
        """
        deploy the helm chart with the given values.yaml,
        patching the values.yaml before deployment:
            - replace the docker user with the given user
            - replace the tag to ensure images are pulled
            - replace the node selector to ensure we only run on nodes that we can observe (require nodes to run scaphandre)
            - apply any patches given in the experiment (see yaml_patch)

        wait for the deployment to be ready, or timeout after 3 minutes
        """

        exp = self.experiment

        with open(
            path.join(exp.env.sut_path, "examples", "helm", "values.yaml"), "r"
        ) as f:
            values = f.read()
            values = values.replace("descartesresearch", exp.env.docker_registry_address)
            # ensure we only run on nodes that we can observe
            values = values.replace(
                r"nodeSelector: {}", r'nodeSelector: {"scaphandre": "true"}'
            )
            values = values.replace("pullPolicy: IfNotPresent", "pullPolicy: Always")
            values = values.replace(r'tag: ""', r'tag: "latest"')
            if exp.autoscaling:
                values = values.replace(r"enabled: false", "enabled: true")
                # values = values.replace(r"clientside_loadbalancer: false",r"clientside_loadbalancer: true")
                if exp.autoscaling == ScalingExperimentSetting.MEMORYBOUND:
                    values = values.replace(
                        r"targetCPUUtilizationPercentage: 80",
                        r"# targetCPUUtilizationPercentage: 80",
                    )
                    values = values.replace(
                        r"# targetMemoryUtilizationPercentage: 80",
                        r"targetMemoryUtilizationPercentage: 80",
                    )
                elif exp.autoscaling == ScalingExperimentSetting.BOTH:
                    values = values.replace(
                        r"targetMemoryUtilizationPercentage: 80",
                        r"targetMemoryUtilizationPercentage: 80",
                    )


        # patches were not in use so disabled for now
        # when reintroducing, should probably get a more meaningful name
        # patch_yaml(values, exp.patches)

        with open(
            path.join(exp.env.sut_path, "examples", "helm", "values.yaml"), "w"
        ) as f:
            f.write(values)

        # write copy of used values to observations
        with open(path.join(observations, "values.yaml"), "w") as f:
            f.write(values)
        try:
            helm_deploy = subprocess.check_output(
                ["helm", "install", "teastore", "-n", exp.namespace, "."],
                cwd=path.join(exp.env.sut_path, "examples", "helm"),
            )
            helm_deploy = helm_deploy.decode("utf-8")
            if not "STATUS: deployed" in helm_deploy:
                print(helm_deploy)
                raise RuntimeError(
                    "failed to deploy helm chart. Run helm install manually and see why it fails"
                )
        except subprocess.CalledProcessError as cpe:
            print(cpe)

        
        self.wait_until_services_ready(
            exp.critical_services,
            180,
            namespace=exp.namespace,
        )

        if exp.autoscaling:
            ExperimentAutoscaling(exp).setup_autoscaling()

    def wait_until_services_ready(self, services, timeout, namespace="default"):

        v1 = kubernetes.client.AppsV1Api()
        ready_services = set()
        start_time = time.time()
        services = set(services)
        print("waiting for deployment to be ready", end="")

        while (
            len(ready_services) < len(services) and time.time() - start_time < timeout
        ):
            for service in services.difference(
                ready_services
            ):  # only check services that are not ready yet
                try:
                    service_status = v1.read_namespaced_stateful_set_status(
                        service, 
                        namespace
                    )
                    if (
                        service_status.status.ready_replicas
                        and service_status.status.ready_replicas > 0
                    ):
                        ready_services.add(service)
                except Exception as e:
                    logging.error(e)
                    pass
            if services == ready_services:
                print("!")
                return True
            time.sleep(1)
            print(".", end="", flush=True)
        raise RuntimeError(
            "Timeout reached. The following services are not ready: "
            + str(list(set(services) - set(ready_services)))
        )
