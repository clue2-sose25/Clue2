import {useContext, useEffect} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {Link} from "react-router";
import {
  FilesIcon,
  RocketLaunchIcon,
  WarningIcon,
  XCircleIcon,
} from "@phosphor-icons/react";
import LogsPanel from "../components/LogsPanel";
import {
  FlaskIcon,
  LightningIcon,
  RepeatIcon,
  WrenchIcon,
} from "@phosphor-icons/react/dist/ssr";

const DashboardPage = () => {
  const {ifDeploying, setIfDeploying, currentDeployment} =
    useContext(DeploymentContext);

  const configItems = [
    {
      label: "SUT (System Under Test)",
      value: currentDeployment.SutName,
      icon: <WrenchIcon size={24} />,
    },
    {
      label: "Experiment",
      value: currentDeployment.experimentName,
      icon: <FlaskIcon size={24} />,
    },
    {
      label: "Workload Type",
      value: currentDeployment.workload,
      icon: <LightningIcon size={24} />,
    },
    {
      label: "Iterations",
      value: currentDeployment.iterations.toLocaleString(),
      icon: <RepeatIcon size={24} />,
    },
    {
      label: "Deploy only",
      value: currentDeployment.deploy_only ? "True" : "False",
      icon: <RepeatIcon size={24} />,
    },
  ];

  useEffect(() => {
    const fetchDeploymentStatus = async () => {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        if (data && typeof data.is_deploying === "boolean") {
          if (ifDeploying !== data.is_deploying) {
            setIfDeploying(data.is_deploying);
          }
        }
      } catch (error) {
        console.error("Failed to fetch deployment status:", error);
      }
    };

    fetchDeploymentStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="w-full h-full flex flex-col gap-6 pt-4 p-6">
      <div className="bg-white p-6 rounded-lg shadow-md w-full">
        <div className="flex gap-6 ">
          <div className="w-1/3">
            {ifDeploying ? (
              <div className="flex flex-col gap-2">
                <div className="pb-2">
                  <p className="flex gap-2 text-xl items-center pt-2 pb-2">
                    <RocketLaunchIcon size={24} /> Deploying{" "}
                    <span className="font-medium">
                      {currentDeployment.SutName}
                    </span>
                    !
                  </p>
                  Your current experiment is being deployed. Please grab a
                  coffee, it may take a while...
                </div>
                <p className="font-medium mb-4">
                  Status: <span className="text-green-400">WAITING...</span>
                </p>
                <div className="mb-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {configItems.map((item, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 p-2 rounded-lg bg-gray-50 hover:bg-gray-100  transition-colors duration-200"
                      >
                        <span className="text-xl flex-shrink-0 mt-0.5">
                          {item.icon}
                        </span>
                        <div className="min-w-0 flex-1">
                          <dt className="text-sm font-medium text-gray-600 mb-1">
                            {item.label}
                          </dt>
                          <dd className="text-sm text-gray-900 font-mono bg-white px-2 py-1 rounded border">
                            {item.value}
                          </dd>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <button
                  className="rounded p-2 bg-green-400 text-white hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  onClick={() => {}}
                  disabled={true}
                >
                  <div className="flex items-center justify-center gap-2">
                    <FilesIcon size={24} className="inline-block" />
                    <span className="font-medium">View results</span>
                  </div>
                </button>
                <button
                  className="rounded p-2 bg-red-400 text-white hover:bg-red-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  onClick={() => {}}
                  disabled={
                    !currentDeployment.SutName ||
                    !currentDeployment.experimentName
                  }
                >
                  <div className="flex items-center justify-center gap-2">
                    <XCircleIcon size={24} className="inline-block" />
                    <span className="font-medium">Cancel experiment</span>
                  </div>
                </button>
              </div>
            ) : (
              <div className="w-full h-[500px]">
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
