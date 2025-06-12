import {useContext, useEffect} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";

const LogsPanel: React.FC = () => {
  const {ifDeploying} = useContext(DeploymentContext);

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
    <div className="flex-1 border p-2 overflow-y-auto h-full w-full bg-black text-white whitespace-pre-wrap">
      {"No logs to show. Please, deploy an experiment..."}
    </div>
  );
};

export default LogsPanel;
