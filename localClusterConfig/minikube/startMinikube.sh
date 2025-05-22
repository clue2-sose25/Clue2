minikube start --insecure-registry "host.internal:6789" --cpus 8 --memory 12000;
kubectl config view --flatten --raw --minify > config_for_clue_deployer
echo "Make sure to switch the commented out volume mount in docker compose before starting the deployer!"