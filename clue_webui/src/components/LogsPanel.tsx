import {useContext, useEffect, useState, useRef} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";

interface LogsResponse {
  logs: string[];
  count: number;
  error?: string;
}

interface LogStreamData {
  log: string;
}

const LogsPanel: React.FC = () => {
  const {ifDeploying} = useContext(DeploymentContext);
  const [logs, setLogs] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs are added
  const scrollToBottom = (): void => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    let es: EventSource | null = null;
    let isMounted = true;
    let pollInterval: number | null = null;

    const fetchLogs = async (): Promise<void> => {
      if (!isMounted) return;

      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch("/api/logs");
        const data: LogsResponse = await res.json();

        if (isMounted) {
          if (data.error) {
            setError(data.error);
            setLogs([]);
          } else {
            // Handle both array and string responses
            const logsArray = Array.isArray(data.logs)
              ? data.logs
              : data.logs
              ? [String(data.logs)]
              : [];
            setLogs(logsArray);
          }
        }
      } catch (err) {
        console.error("Error fetching logs:", err);
        if (isMounted) {
          setError("Failed to load logs.");
          setLogs([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    const setupEventSource = (): void => {
      if (!isMounted) return;

      try {
        es = new EventSource("/api/logs/stream");

        es.onmessage = (e: MessageEvent): void => {
          if (!isMounted) return;

          try {
            const newLogData: LogStreamData = JSON.parse(e.data);
            if (newLogData.log) {
              setLogs((prev) => [...prev, newLogData.log]);
            }
          } catch {
            // If it's just a plain string, add it directly
            setLogs((prev) => [...prev, e.data]);
          }
        };

        es.onerror = (error: Event): void => {
          console.error("EventSource error:", error);
          if (es) {
            es.close();
            es = null;
          }

          // Fallback to polling if EventSource fails
          if (isMounted && ifDeploying) {
            pollInterval = setInterval(fetchLogs, 2000);
          }
        };

        es.onopen = (): void => {
          console.log("EventSource connection opened");
        };
      } catch (error) {
        console.error("Failed to setup EventSource:", error);
        // Fallback to polling
        if (isMounted && ifDeploying) {
          pollInterval = setInterval(fetchLogs, 2000);
        }
      }
    };

    if (ifDeploying) {
      fetchLogs().then(() => {
        // Try to setup EventSource after initial fetch
        setupEventSource();
      });
    } else {
      // If not deploying, just show static message
      setLogs([]);
      setError(null);
      setIsLoading(false);
    }

    return () => {
      isMounted = false;
      if (es) {
        es.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [ifDeploying]);

  const clearLogs = async (): Promise<void> => {
    try {
      const res = await fetch("/api/logs", {method: "DELETE"});
      if (res.ok) {
        setLogs([]);
      }
    } catch (err) {
      console.error("Error clearing logs:", err);
    }
  };

  const renderLogs = (): React.ReactElement => {
    if (isLoading && logs.length === 0) {
      return <div className="text-gray-400 italic">Loading logs...</div>;
    }

    if (error) {
      return <div className="text-red-400">Error: {error}</div>;
    }

    if (!ifDeploying && logs.length === 0) {
      return (
        <div className="text-gray-400 italic">
          No logs to show. Please, deploy an experiment...
        </div>
      );
    }

    if (logs.length === 0) {
      return <div className="text-gray-400 italic">Waiting for logs...</div>;
    }

    return (
      <>
        {logs.map((log, index) => (
          <div key={index} className="whitespace-pre-wrap break-words">
            {log}
          </div>
        ))}
      </>
    );
  };

  return (
    <div className="max-h-[500px] h-full w-full flex flex-col">
      {/* Header with controls */}
      <div className="flex justify-between items-center p-2 bg-gray-800 text-gray-200 text-sm">
        <span className="font-medium">
          Deployment Logs {logs.length > 0 && `(${logs.length} entries)`}
        </span>
        <div className="flex gap-2">
          {ifDeploying && (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-green-400">Live</span>
            </div>
          )}
          <button
            onClick={clearLogs}
            className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded transition-colors"
            title="Clear logs"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Logs container */}
      <div
        ref={logContainerRef}
        className="flex-1 bg-black text-gray-200 p-3 font-mono text-xs overflow-y-auto overflow-x-hidden"
        style={{
          scrollBehavior: "smooth",
          wordBreak: "break-word",
        }}
      >
        {renderLogs()}
      </div>
    </div>
  );
};

export default LogsPanel;
