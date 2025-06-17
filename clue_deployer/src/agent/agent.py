
from io import StringIO ## for Python 3
from flask import Flask,Response, request
from flask_sock import Sock
import csv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Agent")
logger.setLevel(logging.DEBUG)


url = "http://metrics-prometheus-server.prometeus.svc"
if "PROMETHEUSSERVER" in os.environ:
    url = os.environ["PROMETHEUSSERVER"]

if "UPDATE_INTERVAL" in os.environ:
    UPDATE_INTERVAL = int(os.environ["UPDATE_INTERVAL"])
else:
    UPDATE_INTERVAL = 30


namespace = None
if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/namespace"):
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
        namespace = f.read()
elif os.environ.get("NAMESPACE"):
    namespace = os.environ.get("NAMESPACE")
else:
    namespace = "default"
    
from psc import ResourceTracker, FixedQueue, NodeUsage, PodUsage

logger.info("Using namespace %s", namespace)
node_channel = FixedQueue(1024)
pod_channel = FixedQueue(8192)
rt = ResourceTracker(url, node_channel,pod_channel, [namespace], UPDATE_INTERVAL)
rt.start()

app = Flask(f"Prometheus Resource Tracker {namespace}")
sock = Sock(app)
logging.basicConfig(level=logging.ERROR)

def write_csv(channel, size, fields=NodeUsage._fields):
    size = min(size, channel.maxsize)
    data = channel.take(size)
    
    raw = StringIO()
    writer = csv.DictWriter(raw, fieldnames=fields)
    writer.writeheader()
    for p in data:
        writer.writerow(p.to_dict())

    return Response(
        raw.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                    "attachment; filename=metrics.csv"}) 

def sent_csv(websocet, channel, fields=NodeUsage._fields):
    websocet.send(','.join(fields))
    while True:
        p = channel.get().to_dict()
        websocet.send( ','.join([str(p[f]) for f in fields if f in p]))

@app.route('/download', strict_slashes=False)
@app.route('/nodes', strict_slashes=False)
def download_nodes():
    args = request.args
    size = args.get("size", default=90, type=int)
    return write_csv(node_channel, size)

@app.route('/pods', strict_slashes=False)
def download_pods():
    args = request.args
    size = args.get("size", default=90, type=int)
    return write_csv(pod_channel, size, PodUsage._fields)


@sock.route('/metrics', strict_slashes=False)
@sock.route('/metrics/nodes', strict_slashes=False)
def stream_nodes(ws):
    sent_csv(ws, node_channel)

@sock.route('/metrics/pods', strict_slashes=False)
def steam_pods(ws):
    sent_csv(ws, pod_channel, PodUsage._fields)

def main():
    logging.basicConfig(level=logging.ERROR)
    app.run(host='0.0.0.0', port=80)


if __name__ == "__main__":
    main()
