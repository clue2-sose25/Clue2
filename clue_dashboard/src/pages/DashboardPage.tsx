import {useContext} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {Link} from "react-router";
import {RocketIcon, RocketLaunchIcon, WarningIcon} from "@phosphor-icons/react";
import LogsPanel from "../components/LogsPanel";

const DashboardPage = () => {
  const {ifDeploying, currentDeployment} = useContext(DeploymentContext);

  return (
    <div className="w-full h-full flex flex-col gap-6 pt-4 p-6">
      <p className="text-xl font-medium">Dashboard</p>

      <div className="bg-white p-6 rounded-lg shadow-md w-full">
        <div className="flex gap-6 ">
          <div className="w-1/3">
            {ifDeploying ? (
              <div>
                <p className="flex gap-2 text-xl items-center pt-2 pb-4">
                  <RocketLaunchIcon size={24} /> Deploying{" "}
                  <span className="font-medium">
                    {currentDeployment.SutName}
                  </span>
                  !
                </p>
                <p className="font-medium">
                  Status: <span className="text-green-400">WAITING...</span>
                </p>
                <p className="text-gray-600 mt-2">
                  Config:
                  <div>SUT: {currentDeployment.SutName}</div>
                  <div>Experiment: {currentDeployment.experimentName}</div>
                  <div>Workload: {currentDeployment.workload}</div>
                  <div>Iterations: {currentDeployment.iterations}</div>
                </p>
              </div>
            ) : (
              <div>
                <p className="flex gap-2 font-medium text-xl items-center pt-2 pb-4">
                  <WarningIcon size={24} /> No experiment in progress!
                </p>{" "}
                Visit the{" "}
                <Link className="font-medium text-blue-500" to={"/"}>
                  Control Panel
                </Link>{" "}
                to deploy an experiment.
              </div>
            )}
          </div>
          <div className="w-2/3">
            <LogsPanel />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
