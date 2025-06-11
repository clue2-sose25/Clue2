import {useEffect, useState} from "react";

interface LogsPanelProps {
  ifDeploying: boolean;
}

const MAX_LOG_LINES = 200;

const LogsPanel: React.FC<LogsPanelProps> = ({ifDeploying}) => {
  const [logs, setLogs] = useState("");

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
      } catch {
        if (isMounted) setLogs(" no logs yet!");
      }
      es = new EventSource("/api/logs/stream");
      es.onmessage = (e) => {
        if (isMounted) {
          setLogs((prev) => {
            const updated = prev + e.data;
            const lines = updated.split("\n");
            if (lines.length > MAX_LOG_LINES) {
              return lines.slice(-MAX_LOG_LINES).join("\n");
            }
            return updated;
          });
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

  /**
   * Fetch the logs of the CLUE deployer
  //  */
  // useEffect(() => {
  //   if (ifDeploying) {
  //     const loadLogs = () => {
  //       // fetch("/api/logs")
  //       //   .then((r) => r.json())
  //       //   .then((d) => setLogs(d.logs ?? ""))
  //       //   .catch(() => setLogs(""));
  //     };
  //     loadLogs();
  //     // const id = setInterval(loadLogs, 2000);
  //     return () => {}; // () => clearInterval(id);
  //   }
  // }, [ifDeploying]);

  return (
    <div className="flex-1 border p-2 overflow-y-auto h-96 bg-black text-white whitespace-pre-wrap">
      {ifDeploying && (logs || "No logs")}
    </div>
  );
};

export default LogsPanel;
