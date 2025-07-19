import {useContext, useEffect, useState} from "react";
import {Link, useNavigate} from "react-router";
import {
  FilesIcon,
  RocketLaunchIcon,
  SpeedometerIcon,
  WarningIcon,
  XCircleIcon,
  StackIcon,
  TrashIcon,
  XIcon,
  PlayIcon,
} from "@phosphor-icons/react";
import LogsPanel from "../components/LogsPanel";
import {
  FlaskIcon,
  LightningIcon,
  RepeatIcon,
  WrenchIcon,
} from "@phosphor-icons/react/dist/ssr";
import {QueueContext} from "../contexts/QueueContext";
import {IconButton, Dialog, DialogTitle, DialogContent} from "@mui/material";
import type {DeploymentForm} from "../models/DeploymentForm";

const DashboardPage = () => {
  // The experiments queue
  const {currentQueue, setCurrentQueue, setQueueSize, queueSize} =
    useContext(QueueContext);

  // Current deployment state
  const [currentDeployment, setCurrentDeployment] =
    useState<DeploymentForm | null>(null);
  const [deploymentStatus, setDeploymentStatus] = useState<string>("IDLE");

  // Queue modal state
  const [showQueueModal, setShowQueueModal] = useState(false);

  const navigate = useNavigate();

  /**
   * Fetch current deployment from the API
   */
  const fetchCurrentDeployment = async () => {
    try {
      const response = await fetch("/api/queue/current");
      if (!response.ok) {
        // Handle 404 or other expected "no current deployment" responses
        if (response.status === 404) {
          setCurrentDeployment(null);
          setDeploymentStatus("IDLE");
          return;
        }
        throw new Error(`API responded with status ${response.status}`);
      }

      const data = await response.json();

      // Handle explicit null response
      if (data === null || data === undefined) {
        setCurrentDeployment(null);
        setDeploymentStatus("IDLE");
        return;
      }

      // Handle empty object or invalid data
      if (typeof data !== "object" || !data.sut) {
        console.warn("Received invalid deployment data:", data);
        setCurrentDeployment(null);
        setDeploymentStatus("IDLE");
        return;
      }

      // Valid deployment data
      setCurrentDeployment(data);
      setDeploymentStatus(data.status || "DEPLOYING...");
    } catch (err) {
      console.error("Failed to fetch current deployment:", err);
      setCurrentDeployment(null);
      setDeploymentStatus("ERROR");
    }
  };

  /**
   * Fetch queue data from the API
   */
  const fetchQueue = async () => {
    try {
      const response = await fetch("/api/queue/status");
      if (!response.ok) {
        throw new Error(`API responded with status ${response.status}`);
      }
      const data = await response.json();

      // Validate that we received the expected object structure
      if (!data || typeof data !== "object") {
        console.error("API returned invalid data:", data);
        setCurrentQueue([]);
        setQueueSize(0);
        return;
      }

      // Ensure queue is an array
      if (!Array.isArray(data.queue)) {
        console.error("API returned non-array queue:", data.queue);
        setCurrentQueue([]);
        setQueueSize(data.queue_size || 0);
        return;
      }

      setCurrentQueue(data.queue ?? []);
      setQueueSize(data.queue_size || 0);
    } catch (err) {
      console.error("Failed to fetch queue:", err);
      setCurrentQueue([]);
      setQueueSize(0);
    }
  };

  /**
   * Remove item from queue
   */
  const removeFromQueue = async (index: number) => {
    try {
      const response = await fetch(`/api/queue/remove/${index}`, {
        method: "DELETE",
      });
      if (response.ok) {
        await fetchQueue(); // Refresh queue
      }
    } catch (err) {
      console.error("Failed to remove item from queue:", err);
    }
  };

  /**
   * Clear entire queue
   */
  const clearQueue = async () => {
    try {
      const response = await fetch("/api/queue/flush", {
        method: "DELETE",
      });
      if (response.ok) {
        await fetchQueue(); // Refresh queue
        setShowQueueModal(false);
      }
    } catch (err) {
      console.error("Failed to clear queue:", err);
    }
  };

  /**
   * Start deployment from queue
   */
  const startDeployment = async () => {
    try {
      const response = await fetch("/api/queue/deploy", {
        method: "POST",
      });
      if (response.ok) {
        await fetchCurrentDeployment(); // Refresh current deployment
        await fetchQueue(); // Refresh queue
      }
    } catch (err) {
      console.error("Failed to start deployment:", err);
    }
  };

  const cancelCurrentExperiment = async () => {
    try {
      const response = await fetch("/api/queue/stop", {
        method: "DELETE",
      });
      if (response.ok) {
        await fetchCurrentDeployment(); // Refresh current deployment
      }
    } catch (err) {
      console.error("Failed to cancel experiment:", err);
    }
  };

  /**
   * On the component load
   */
  useEffect(() => {
    fetchQueue();
    fetchCurrentDeployment();

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      fetchQueue();
      fetchCurrentDeployment();
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Helper function to safely access deployment properties
  const getDeploymentValue = (
    key: keyof DeploymentForm,
    defaultValue: any = "N/A"
  ) => {
    if (!currentDeployment) return defaultValue;
    const value = currentDeployment[key];
    if (value === null || value === undefined) return defaultValue;
    return value;
  };

  const configItems = [
    {
      label: "SUT (System Under Test)",
      value: getDeploymentValue("sut"),
      icon: <WrenchIcon size={24} />,
    },
    {
      label: "Experiments",
      value: Array.isArray(getDeploymentValue("variants"))
        ? getDeploymentValue("variants").join(", ")
        : "N/A",
      icon: <FlaskIcon size={24} />,
    },
    {
      label: "Workload Type",
      value: Array.isArray(getDeploymentValue("workloads"))
        ? getDeploymentValue("workloads").join(", ")
        : "N/A",
      icon: <LightningIcon size={24} />,
    },
    {
      label: "Iterations",
      value: getDeploymentValue("iterations", 0)?.toLocaleString() || "0",
      icon: <RepeatIcon size={24} />,
    },
    {
      label: "Deploy only",
      value: getDeploymentValue("deploy_only", false) ? "True" : "False",
      icon: <RepeatIcon size={24} />,
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case "DEPLOYING...":
      case "DEPLOYING":
        return "text-blue-500";
      case "RUNNING":
        return "text-green-500";
      case "COMPLETED":
        return "text-green-600";
      case "ERROR":
      case "FAILED":
        return "text-red-500";
      case "CANCELLED":
        return "text-orange-500";
      case "IDLE":
        return "text-gray-500";
      default:
        return "text-gray-500";
    }
  };

  // Check if we have a valid deployment
  const hasValidDeployment =
    currentDeployment &&
    currentDeployment.sut &&
    typeof currentDeployment.sut === "string" &&
    currentDeployment.sut.trim() !== "";

  return (
    <div className="w-full h-full flex flex-col gap-2">
      <div className="bg-white p-6 rounded-lg shadow-md w-full h-full relative">
        {/* Queue Status Button */}
        <div className="absolute top-6 right-6 z-10 flex gap-2">
          <button
            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
            onClick={startDeployment}
            disabled={queueSize === 0 || hasValidDeployment}
          >
            <PlayIcon size={18} />
            <span>Start Next</span>
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2 bg-blue-400 text-white rounded hover:bg-blue-600 transition-colors font-medium"
            onClick={() => setShowQueueModal(true)}
          >
            <StackIcon size={18} />
            <span>
              Queue ({queueSize} {queueSize === 1 ? "item" : "items"})
            </span>
          </button>
        </div>

        {hasValidDeployment ? (
          <div className="flex gap-6 h-full">
            <div className="w-1/3">
              <div className="flex flex-col gap-2">
                <div className="pb-2">
                  <p className="flex gap-2 text-xl items-center pt-2 pb-2">
                    <RocketLaunchIcon size={24} /> Deploying{" "}
                    <span className="font-medium">
                      {getDeploymentValue("sut")}
                    </span>
                    !
                  </p>
                  Your current experiment is being deployed. Please grab a
                  coffee, it may take a while...
                </div>
                <p className="font-medium mb-4">
                  Status:{" "}
                  <span className={getStatusColor(deploymentStatus)}>
                    {deploymentStatus}
                  </span>
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
                  onClick={cancelCurrentExperiment}
                  disabled={
                    !hasValidDeployment || deploymentStatus === "COMPLETED"
                  }
                >
                  <div className="flex items-center justify-center gap-2">
                    <XCircleIcon size={24} className="inline-block" />
                    <span className="font-medium">Cancel experiment</span>
                  </div>
                </button>
              </div>
            </div>
            <div className="w-2/3 flex flex-col gap-2">
              <LogsPanel />
              <span className="flex gap-2 p-1 items-center">
                <SpeedometerIcon size={32} />
                To see more live metrics visit the
                <Link
                  className="text-blue-500 cursor-pointer"
                  to={"http://localhost:3000"}
                >
                  Grafana dashboard
                </Link>
              </span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center w-full h-full justify-center">
            <span className="flex flex-col font-semibold text-xl items-center pb-2 gap-2">
              <WarningIcon size={90} /> No active deployment!
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

      {/* Queue Modal */}
      <Dialog
        open={showQueueModal}
        onClose={() => setShowQueueModal(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{
          className: "max-h-[80vh] rounded-lg shadow-xl",
        }}
      >
        <DialogTitle className="flex justify-between items-center p-4 border-b border-gray-200">
          <div>
            <span className="text-xl font-medium">
              Experiment Queue ({queueSize} items)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={startDeployment}
              className="flex items-center gap-2 px-3 py-2 bg-green-400 text-white rounded hover:bg-green-600 transition-colors font-medium text-sm disabled:bg-gray-400 disabled:cursor-not-allowed"
              disabled={queueSize === 0 || hasValidDeployment}
            >
              <PlayIcon size={16} />
              Start Next
            </button>
            <button
              onClick={clearQueue}
              className="flex items-center gap-2 px-3 py-2 bg-red-400 text-white rounded hover:bg-red-600 transition-colors font-medium text-sm disabled:bg-gray-400 disabled:cursor-not-allowed"
              disabled={queueSize === 0}
            >
              <TrashIcon size={16} />
              Clear All
            </button>
            <IconButton
              aria-label="close"
              onClick={() => setShowQueueModal(false)}
              className="text-gray-500 hover:text-gray-700 transition-colors"
            >
              <XIcon size={24} />
            </IconButton>
          </div>
        </DialogTitle>

        <DialogContent className="p-6">
          {currentQueue.length === 0 ? (
            <div className="text-center py-8 text-gray-500">Queue is empty</div>
          ) : (
            <div className="space-y-3">
              {currentQueue.map((item, index) => (
                <div
                  key={index}
                  className="border rounded-lg p-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex-1">
                    <div className="font-medium text-lg mb-2">
                      {item.sut || "Unknown SUT"}
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Experiments:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {Array.isArray(item.variants) &&
                          item.variants.length > 0
                            ? item.variants.join(", ")
                            : "N/A"}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Workloads:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {Array.isArray(item.workloads) &&
                          item.workloads.length > 0
                            ? item.workloads.join(", ")
                            : "N/A"}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Iterations:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {item.iterations &&
                          typeof item.iterations === "number"
                            ? item.iterations.toLocaleString()
                            : "0"}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Deploy only:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {item.deploy_only ? "True" : "False"}
                        </div>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFromQueue(index)}
                    className="ml-4 p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                    title="Remove from queue"
                  >
                    <XCircleIcon size={20} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DashboardPage;
