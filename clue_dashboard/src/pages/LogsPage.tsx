import { useState, useEffect } from "react";

const LogsPage = () => {
  const [logs, setLogs] = useState<string>("Fetching logs...");
  
  useEffect(() => {
    let isMounted = true;
    const fetchLogs = async () => {
      try {
        const res = await fetch("/api/logs");
        const text = await res.text();
        if (isMounted) {
          setLogs(text);
        }
      } catch (err) {
        console.error("Error fetching logs:", err);
        if (isMounted) {
          setLogs("Failed to load logs.");
        }
      }
    };

    // Initial fetch and then interval
    fetchLogs();
    const intervalId = setInterval(fetchLogs, 3000);  // poll every 3 seconds

    // Cleanup on unmount
    return () => {
      isMounted = false;
      clearInterval(intervalId);
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
