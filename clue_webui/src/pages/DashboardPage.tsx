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

  // Loading states
  const [isStartingDeployment, setIsStartingDeployment] = useState(false);

  const navigate = useNavigate();

  /**
   * Fetch current deployment from the API
   */
  const fetchCurrentDeployment = async () => {
    try {
      const response = await fetch("/api/queue/current");
      if (!response.ok) {
        throw new Error(`API responded with status ${response.status}`);
      }
      const data = await response.json();

      if (data) {
        setCurrentDeployment(data);
        // Set status based on deployment state - you can adjust this logic based on your backend
        setDeploymentStatus(data.status || "DEPLOYING...");
      } else {
        setCurrentDeployment(null);
        setDeploymentStatus("IDLE");
      }
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
        return {queue: [], queue_size: 0};
      }

      // Ensure queue is an array
      if (!Array.isArray(data.queue)) {
        console.error("API returned non-array queue:", data.queue);
        return {queue: [], queue_size: data.queue_size || 0};
      }

      setCurrentQueue(data.queue ?? []);
      setQueueSize(data.queue_size);
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
    // Note: You might need to implement a specific endpoint for removing individual items
    // For now, this is a placeholder - you'd need to add this endpoint to your backend
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
    setIsStartingDeployment(true);

    try {
      const response = await fetch("/api/queue/deploy", {
        method: "POST",
      });
      if (response.ok) {
        // Close the modal immediately for better UX
        setShowQueueModal(false);

        // Give the backend worker time to start before fetching status
        setTimeout(async () => {
          await Promise.all([fetchCurrentDeployment(), fetchQueue()]);
        }, 2000); // 2 second delay to allow worker to start
      }
    } catch (err) {
      console.error("Failed to start deployment:", err);
    } finally {
      // Keep loading state for a bit longer to show feedback
      setTimeout(() => {
        setIsStartingDeployment(false);
      }, 2000);
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
    // const interval = setInterval(() => {
    //   fetchQueue();
    //   fetchCurrentDeployment();
    // }, 5000);

    // return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const configItems = [
    {
      label: "SUT (System Under Test)",
      value: currentDeployment?.sut || "N/A",
      icon: <WrenchIcon size={24} />,
    },
    {
      label: "Experiments",
      value: currentDeployment?.variants?.join(", ") || "N/A",
      icon: <FlaskIcon size={24} />,
    },
    {
      label: "Workload Type",
      value: currentDeployment?.workloads?.join(", ") || "N/A",
      icon: <LightningIcon size={24} />,
    },
    {
      label: "Iterations",
      value: currentDeployment?.n_iterations?.toLocaleString() || "0",
      icon: <RepeatIcon size={24} />,
    },
    {
      label: "Deploy only",
      value: currentDeployment?.deploy_only ? "True" : "False",
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
      default:
        return "text-gray-500";
    }
  };

  const isStartButtonDisabled =
    queueSize === 0 || !!currentDeployment || isStartingDeployment;

  return (
    <div className="w-full h-full flex flex-col gap-2">
      <div className="bg-white p-6 rounded-lg shadow-md w-full h-full flex flex-col">
        {/* Queue Control Section - Always visible at top */}
        <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-200">
          <div className="font-large text-lg font-semibold">
            CLUE2 Dashboard
          </div>
          <div className="flex gap-2">
            <button
              className="flex items-center gap-2 px-4 py-2 bg-green-400 text-white rounded hover:bg-green-600 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
              onClick={startDeployment}
              disabled={isStartButtonDisabled}
            >
              {isStartingDeployment ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  <span>Starting...</span>
                </>
              ) : (
                <>
                  <PlayIcon size={18} />
                  <span>Start Next</span>
                </>
              )}
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
        </div>

        {/* Main Content Area */}
        <div className="flex-1">
          {currentDeployment ? (
            <div className="flex gap-6 h-full">
              <div className="w-1/3">
                <div className="flex flex-col gap-2">
                  <div className="pb-2">
                    <p className="flex gap-2 text-xl items-center pt-2 pb-2">
                      <RocketLaunchIcon size={24} /> Deploying{" "}
                      <span className="font-medium">
                        {currentDeployment.sut}
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
                      !currentDeployment.sut || deploymentStatus === "COMPLETED"
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
              disabled={isStartButtonDisabled}
            >
              {isStartingDeployment ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Starting...
                </>
              ) : (
                <>
                  <PlayIcon size={16} />
                  Start Next
                </>
              )}
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
                    <div className="font-medium text-lg mb-2">{item.sut}</div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">Experiments:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {item.variants?.join(", ") || "N/A"}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Workloads:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {item.workloads?.join(", ") || "N/A"}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Iterations:</span>
                        <div className="font-mono bg-white px-2 py-1 rounded border mt-1">
                          {item.n_iterations?.toLocaleString() || "0"}
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
