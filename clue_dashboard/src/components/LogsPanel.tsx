import {useContext, useEffect, useState} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";

const LogsPanel: React.FC = () => {
  const {ifDeploying} = useContext(DeploymentContext);
  const [logs, setLogs] = useState<string>(
    "No logs to show. Please, deploy an experiment..."
  );

  useEffect(() => {
    let es: EventSource | null = null;
    let isMounted = true;

    const fetchLogs = async () => {
      try {
        const res = await fetch("/api/logs");
        const data = await res.json();
        if (isMounted) {
          setLogs(data.logs ?? "");
        }
      } catch (err) {
        console.error("Error fetching logs:", err);
        if (isMounted) {
          setLogs("Failed to load logs.");
        }
      }
      es = new EventSource("/api/logs/stream");
      es.onmessage = (e) => {
        if (isMounted) {
          setLogs((prev) => prev + e.data);
        }
      };
      es.onerror = () => {
        if (es) es.close();
      };
    };

    if (ifDeploying) {
      fetchLogs();
      return () => {
        isMounted = false;
        if (es) es.close();
      };
    }
  }, [ifDeploying]);

  return (
    <div className="h-full w-full">
      <pre className="bg-black text-gray-200 p-3 rounded font-mono text-xs w-full h-full overflow-y-scroll">
        {logs}
      </pre>
    </div>
  );
};

export default LogsPanel;
