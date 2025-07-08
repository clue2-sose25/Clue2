import {useContext, useEffect, useState} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {Link, useNavigate} from "react-router";
import {
  CaretLeftIcon,
  CaretRightIcon,
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
import {QueueContext} from "../contexts/QueueContext";
import {IconButton} from "@mui/material";

const DashboardPage = () => {
  const {ifDeploying, setIfDeploying, currentDeployment} =
    useContext(DeploymentContext);

  // The experiments queue
  const {currentQueue, setCurrentQueue} = useContext(QueueContext);
  // The currently displayed index from queue
  const [currentQueueIndex, setCurrentQueueIndex] = useState<number>(0);

  const navigate = useNavigate();

  /**
   * On the component load
   */
  useEffect(() => {
    fetch("/api/queue")
      .then(async (r) => {
        if (!r.ok) {
          throw new Error(`API responded with status ${r.status}`);
        }
        const data = await r.json();
        // Validate data type (optional, adjust based on your needs)
        if (!Array.isArray(data)) {
          console.error("API returned non-array data:", data);
          return [];
        }
        return data;
      })
      .then((d) => setCurrentQueue(d ?? []))
      .catch((err) => {
        console.error("Failed to fetch queue:", err);
        setCurrentQueue([]);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const configItems = [
    {
      label: "SUT (System Under Test)",
      value: currentDeployment.sut,
      icon: <WrenchIcon size={24} />,
    },
    {
      label: "Experiments",
      value: currentDeployment.variants.join(", "),
      icon: <FlaskIcon size={24} />,
    },
    {
      label: "Workload Type",
      value: currentDeployment.workloads.join(", "),
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

  const increaseIndexInQueue = () => {
    if (currentQueue.length > currentQueueIndex) {
      setCurrentQueueIndex(currentQueueIndex + 1);
    }
  };

  const decreaseIndexInQueue = () => {
    if (currentQueueIndex > 0) {
      setCurrentQueueIndex(currentQueueIndex - 1);
    }
  };

  return (
    <div className="w-full h-full flex flex-col gap-2">
      {ifDeploying && (
        <div className="w-full h-full flex items-center justify-center gap-2">
          <IconButton
            disabled={currentQueueIndex <= 0}
            onClick={decreaseIndexInQueue}
          >
            <CaretLeftIcon size={18}></CaretLeftIcon>
          </IconButton>
          <span className="font-medium select-none">
            Experiment {currentQueue.length > 0 ? currentQueueIndex + 1 : 0}/
            {currentQueue.length}
          </span>
          <IconButton
            disabled={
              currentQueueIndex >= currentQueue.length - 1 || !currentQueue
            }
            onClick={increaseIndexInQueue}
          >
            <CaretRightIcon size={18}></CaretRightIcon>
          </IconButton>
        </div>
      )}
      <div className="bg-white p-6 rounded-lg shadow-md w-full h-full">
        {!ifDeploying ? (
          <div className="flex gap-6 ">
            <div className="w-1/3">
              <div className="flex flex-col gap-2">
                <div className="pb-2">
                  <p className="flex gap-2 text-xl items-center pt-2 pb-2">
                    <RocketLaunchIcon size={24} /> Deploying{" "}
                    <span className="font-medium">{currentDeployment.sut}</span>
                    !
                  </p>
                  Your current experiment is being deployed. Please grab a
                  coffee, it may take a while...
                </div>
                <p className="font-medium mb-4">
                  Status: <span className="text-green-400">DEPLOYING...</span>
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
                  className="rounded p-2 bg-blue-400 text-white hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  onClick={() => {
                    navigate("/results");
                  }}
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
                    !currentDeployment.sut ||
                    currentDeployment.variants.length === 0
                  }
                >
                  <div className="flex items-center justify-center gap-2">
                    <XCircleIcon size={24} className="inline-block" />
                    <span className="font-medium">Cancel experiment</span>
                  </div>
                </button>
              </div>
            </div>
            <div className="w-2/3">
              <LogsPanel />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center w-full h-full justify-center">
            <span className="flex flex-col font-semibold text-xl items-center pb-2 gap-2">
              <WarningIcon size={90} /> The queue is empty!
            </span>{" "}
            <span>
              Add a{" "}
              <Link
                className="font-medium text-sm text-blue-500"
                to={"/experiment"}
              >
                new experiment
              </Link>{" "}
              to the queue!
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
