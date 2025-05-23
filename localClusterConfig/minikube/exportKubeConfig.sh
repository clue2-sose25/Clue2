kubectl config view --flatten --raw --minify > minikube_kube_config
echo "Make sure to switch the commented out volume mount in docker compose before starting the deployer!"