import { useState, useEffect } from "react";

interface LogViewerProps {
  refreshIntervalMs?: number;
  heightClass?: string;
}

const LogViewer = ({ refreshIntervalMs = 3000, heightClass = "h-64" }: LogViewerProps) => {
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

    fetchLogs();
    const id = setInterval(fetchLogs, refreshIntervalMs);
    return () => {
      isMounted = false;
      clearInterval(id);
    };
  }, [refreshIntervalMs]);

  return (
    <pre className={`bg-black text-gray-200 p-3 rounded font-mono text-xs overflow-y-scroll ${heightClass}`}>{logs}</pre>
  );
};

export default LogViewer;
