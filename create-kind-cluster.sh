#!/bin/bash
set -e

CLUSTER_NAME=clue-cluster
NETWORK_NAME=clue2
KIND_CONFIG=./kind-config.yaml

# Create network if it doesn't exist
docker network inspect $NETWORK_NAME >/dev/null 2>&1 || {
  echo "Creating docker network $NETWORK_NAME"
  docker network create $NETWORK_NAME
}

# Create Kind cluster
echo "Creating Kind cluster: $CLUSTER_NAME"
kind create cluster --name "$CLUSTER_NAME" --config "$KIND_CONFIG"

# Connect Kind nodes to the Docker network
echo "Connecting Kind nodes to $NETWORK_NAME"
for node in $(kind get nodes --name "$CLUSTER_NAME"); do
  docker network connect "$NETWORK_NAME" "$node" || true
done

echo "Kind cluster '$CLUSTER_NAME' is now connected to Docker network '$NETWORK_NAME'"
