import {useEffect, useState} from "react";

interface LogsPanelProps {
  ifDeploying: boolean;
}

const LogsPanel: React.FC<LogsPanelProps> = ({ifDeploying}) => {
  const [logs, setLogs] = useState<string>("");

  /**
   * Fetch the logs of the CLUE deployer
   */
  useEffect(() => {
    if (ifDeploying) {
      const loadLogs = () => {
        fetch("/api/logs")
          .then((r) => r.json())
          .then((d) => setLogs(d.logs ?? ""))
          .catch(() => setLogs(""));
      };
      loadLogs();
      const id = setInterval(loadLogs, 2000);
      return () => clearInterval(id);
    }
  }, [ifDeploying]);

  return (
    <div className="flex-1 border p-2 overflow-y-auto h-96 bg-black text-white whitespace-pre-wrap">
      {logs || "No logs"}
    </div>
  );
};

export default LogsPanel;
