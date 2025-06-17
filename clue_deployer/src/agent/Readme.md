# Prometheus Scraphandre Collector Agent

Prometheus-Agent is a simple Prometheus agent that periodically queries Prometheus to fetch measurement data for the namespace in which the agent is deployed.

Credits: Sebastian Werner (GitHub: @tawalaya) and Karl Wolf (GitHub @wolfkarl)

## API

The agent supports two endpoints:

- `/download`: Sends the last 100 measurements observed as a CSV file.
- `/metrics`: Returns a WebSocket connection to stream measurements as a CSV file.
- `/nodes`: Returns a CSV file with the last 100 measurements of the nodes.
- `/pods`: Returns a CSV file with the last 100 measurements of the pods in the namespace.
- `/metrics/nodes`: Returns a WebSocket connection to stream measurements of the nodes as a CSV file.
- `/metrics/pods`: Returns a WebSocket connection to stream measurements of the pods as a CSV file.

## Data

The returned CSV data from the API contains the following fields for nodes:

| Name             | Format     | Description                                                                                 |
| ---------------- | ---------- | ------------------------------------------------------------------------------------------- |
| instance         | String     | The name of the Kubernetes node that was measured.                                          |
| collection_time  | ISO-Time   | The time of the query request.                                                              |
| observation_time | ISO-Time   | The time of the measurement.                                                                |
| cpu_usage        | Rate       | The rate of CPU seconds utilzed during the measurement window.                              |
| memory_usage     | Percentage | The percentage of memory utilized during the measurement window.                            |
| network_usage    | Fraction   | The total number of bytes sent and received within the measurement window.                  |
| wattage          | Watt/h     | The total watt/h consumed by the node during the measurement window.                        |
| num_processes    | Number     | The total number of processes running on the node.                                          |
| kepler_wattage   | Watt/s     | The watt/s measured by Kepler on the node.                                                  |
| scaph_wattage    | Watt/s     | The watt/s measured by scraphandre on the node.                                             |
| wattage_auxilary | Watt/s     | The microwatts measured scraphandre that can not be attributed to a specific pod/container. |

The returned CSV data from the API contains the following fields for pods:
| Name | Format | Description |
|-----------------|--------------|------------------------------------------------------|
| instance | String | The name of the Kubernetes pod that was measured. |
| collection_time | ISO-Time | The time of the query request. |
| observation_time | ISO-Time | The time of the measurement. |
| name | String | The name of the pod. |
| namespace | String | The namespace of the pod. |
| cpu_usage | Rate | The rate of CPU seconds utilized during the measurement window. |
| memory_usage | MB | The average of memory utilization (in bytes) during the measurement. |
| network_usage | Rate | The rate MB sent or received within the measurement window. |
| wattage_kepler | Watt | The Watt/s measured by Kepler for the pod. |
| wattage_scaph | Watt | The Watt/s measured by scraphandre for the pod. |

## Deployment and Usage

1. Build the Docker image with `<tag>` and push the image.
2. Edit the `kustomization.yaml` file with the new `<tag>` and `<namespace>` you want to observe. Also don't forget to set the `<prometeus-address>` to the address of the prometues server.
3. Run `kubectl apply -k .`.
4. Run `kubectl port-forward -n <namespace>  prometheus-agent 8000` in a separate terminal.
5. Use a tool like [websocat](https://github.com/vi/websocat) to stream experiment observations. For example, you can use `websocat ws://127.0.0.1:8000/metrics > example.csv` to save the streamed data to a CSV file.
