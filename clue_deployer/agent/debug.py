import time

from psc import ResourceTracker, FixedQueue, NodeUsage
def main(url, namespace, ):
    nodes = FixedQueue(128)
    pods = FixedQueue(128)
    rt = ResourceTracker(url, nodes,pods, [namespace], 30)
    rt.start()

    time.sleep(40)
    rt.stop()
    for n in nodes.elements():
        print(n)
    
    for p in pods.elements():
        print(p.to_dict())

if __name__ == "__main__":
    url = "ADD YOUR URL HERE"
    namespace = "ADD YOUR NAMESPACE HERE"
    main(url,namespace)
