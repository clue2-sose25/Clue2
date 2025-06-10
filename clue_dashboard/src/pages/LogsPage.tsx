import { useState, useEffect } from "react";

const LogsPage = () => {
  const [logs, setLogs] = useState<string>("Fetching logs...");
  
  useEffect(() => {
    let es: EventSource | null = null;
    let isMounted = true;

    const init = async () => {
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

    init();

    return () => {
      isMounted = false;
      if (es) es.close();
    };
  }, []);

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-2">Deployer Logs</h2>
      <pre className="bg-black text-gray-200 p-3 rounded font-mono text-xs h-64 overflow-y-scroll">
        {logs}
      </pre>
    </div>
  );
};

export default LogsPage;
