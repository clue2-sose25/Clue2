import {useContext, useEffect} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {RocketLaunchIcon, StackPlusIcon} from "@phosphor-icons/react";
import {useNavigate} from "react-router";
import {QueueContext} from "../contexts/QueueContext";
import ParametersSelection from "../components/experiment/ParametersSelection";
import EstimationTime from "../components/experiment/EstimationTime";

const ExperimentPage = () => {
  const {currentDeployment, setIfDeploying} = useContext(DeploymentContext);
  const {currentQueue, setCurrentQueue} = useContext(QueueContext);

  const navigate = useNavigate();

  // System Under Test - Progress
  const sutConfigProgress =
    !!currentDeployment.sut &&
    currentDeployment.variants.length > 0 &&
    (currentDeployment.deploy_only || currentDeployment.workloads.length > 0);

  const benchmarkingConfigProgress = currentDeployment.iterations > 0;
  const deployEnabled = sutConfigProgress && benchmarkingConfigProgress;

  /**
   * On the component load
   */
  useEffect(() => {
    fetchQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchQueue = () => {
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
  };

  const deploySUT = async () => {
    if (!deployEnabled) return;

    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        sut: currentDeployment.sut,
        variants: currentDeployment.variants.join(","),
        workloads: currentDeployment.workloads.join(","),
        n_iterations: currentDeployment.iterations,
        deploy_only: currentDeployment.deploy_only,
      }),
    });

    setIfDeploying(true);
    fetchQueue();
    navigate("/dashboard");
  };

  return (
    <div className="w-full h-full flex flex-col items-center">
      <div className="h-[calc(100%-3.5rem)] flex flex-col md:flex-row gap-4 w-full justify-center">
        {/* Progress Sidebar */}
        <div className="h-full border-x border-t rounded shadow p-4 flex flex-col gap-2 md:w-1/5">
          <p className="font-medium">Configuration Progress</p>
          <label className="flex gap-2 items-center">
            <input
              type="checkbox"
              readOnly
              checked={sutConfigProgress}
              className="w-5 h-5"
            />
            <span>System Under Test</span>
          </label>
          <label className="flex gap-2 items-center">
            <input
              type="checkbox"
              readOnly
              checked={benchmarkingConfigProgress}
              className="w-5 h-5"
            />
            <span>Benchmarking Options</span>
          </label>
        </div>

        {/* Parameter Selection Component */}
        <ParametersSelection />

        {/* Estimated Benchmarking Time Component */}
        <EstimationTime />
      </div>
      <div className="flex w-full justify-start h-[3.5rem] p-2 border rounded shadow gap-2">
        {/* Deploy Button */}
        <div className="h-full p-4 flex flex-col gap-2 md:w-1/5"></div>
        <button
          className={`rounded py-2 px-4 ${
            !deployEnabled
              ? "bg-gray-300 text-gray-500"
              : "bg-blue-500 text-white hover:bg-blue-700"
          }`}
          onClick={deploySUT}
          disabled={!deployEnabled}
        >
          {currentQueue ? (
            <div className="flex items-center justify-center gap-2">
              <RocketLaunchIcon size={24} className="inline-block" />
              <span className="font-medium">Add experiment to the queue</span>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2">
              <StackPlusIcon size={24} className="inline-block" />
              <span className="font-medium">Queue experiment</span>
            </div>
          )}
        </button>
      </div>
    </div>
  );
};

export default ExperimentPage;
