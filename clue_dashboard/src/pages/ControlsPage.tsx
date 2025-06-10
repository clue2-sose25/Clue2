import {useEffect, useState, type ChangeEvent} from "react";
import type {Deployment as DeploymentForm} from "../models/Deployment";
import LogsPanel from "../components/LogsPanel";
import {InfoIcon} from "@phosphor-icons/react";
import type {SUT} from "../models/SUT";

const workloadOptions = ["shaped", "rampup", "pausing", "fixed"];

const ControlsPage = () => {
  const defaultDeploymentForm: DeploymentForm = {
    SutName: null,
    experimentName: null,
    workload: "shaped",
    iterations: 1,
  };

  const [currentDeployment, setCurrentDeployment] = useState<DeploymentForm>(
    defaultDeploymentForm
  );
  const [ifDeploying, setIfDeploying] = useState<boolean>(false);
  const [availableSUTs, setAvailableSUTs] = useState<SUT[]>([]);
  const [deployOnly, setDeployOnly] = useState(false);

  /**
   * Fetches the list of available SUTs
   */
  useEffect(() => {
    fetch("/api/list/sut")
      .then((r) => r.json())
      .then((d) => setAvailableSUTs(d.suts ?? []))
      .catch(() => setAvailableSUTs([]));
  }, []);

  /**
   * Handles the change of the SUT
   * @param e Change event
   */
  const handleSutSelection = (e: ChangeEvent<HTMLSelectElement>) => {
    setCurrentDeployment({
      ...currentDeployment,
      SutName: e.target.value,
      experimentName: null,
    });
  };

  /**
   * Handles the change in the experiment
   * @param e Change event
   */
  const handleExperimentSelection = (e: ChangeEvent<HTMLSelectElement>) => {
    setCurrentDeployment({
      ...currentDeployment,
      experimentName: e.target.value,
    });
  };

  /**
   * Deploys a SUT
   */
  const deploy = async () => {
    if (!currentDeployment.SutName || !currentDeployment.experimentName) return;
    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        sut_name: currentDeployment.SutName,
        experiment_name: currentDeployment.experimentName,
      }),
    });
    setIfDeploying(true);
  };

  return (
    <div className="w-full h-full flex flex-col items-center gap-6 pt-4">
      <div className="flex flex-col items-center">
        <p className="text-xl font-medium">Deploy CLUE</p>
        <p>Choose your parameters for the benchmark</p>
      </div>
      <div className="flex flex-col gap-4 w-1/3">
        {/* SUT Dropdown */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="sut-select"
            className="flex gap-2 items-center text-sm font-medium"
          >
            SUT <InfoIcon size={18} />
          </label>
          <select
            id="sut-select"
            className="border p-2 w-full"
            value={currentDeployment.SutName || ""}
            onChange={(e) => handleSutSelection(e)}
          >
            <option value="" disabled>
              {availableSUTs.length > 0 ? "Select SUT" : "Loading SUTs..."}
            </option>
            {availableSUTs.map((sut) => (
              <option key={sut.name} value={sut.name}>
                {sut.name}
              </option>
            ))}
          </select>
        </div>
        {/* Experiment Dropdown */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="experiment-select"
            className="flex gap-2 items-center text-sm font-medium"
          >
            Experiment <InfoIcon size={18} />
          </label>
          <select
            id="experiment-select"
            className={`border py-2 px-4 w-full ${
              !currentDeployment.SutName ? "opacity-50" : ""
            }`}
            value={currentDeployment.experimentName || ""}
            onChange={(e) => handleExperimentSelection(e)}
            disabled={!currentDeployment.SutName}
          >
            <option value="" disabled>
              Select Experiment
            </option>
            {availableSUTs
              .filter((sut) => sut.name === currentDeployment.SutName)
              .flatMap((sut) => sut.experiments)
              .map((exp) => (
                <option key={exp} value={exp}>
                  {exp}
                </option>
              ))}
          </select>
        </div>
        {/* Workload Type Dropdown */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="workload-select"
            className="flex gap-2 items-center text-sm font-medium text-nowrap"
          >
            Workload Type <InfoIcon size={18} />
          </label>
          <select
            id="workload-select"
            className="border p-2 w-full"
            value={currentDeployment.workload || ""}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                workload: e.target.value,
              })
            }
          >
            {workloadOptions.map((w) => (
              <option key={w} value={w}>
                {w}
              </option>
            ))}
          </select>
        </div>
        {/* Iterations Input */}
        <div className="flex flex-col gap-2">
          <label
            htmlFor="iterations-input"
            className="flex gap-2 items-center text-sm font-medium text-nowrap"
          >
            Iterations <InfoIcon size={18} />
          </label>
          <input
            id="iterations-input"
            type="number"
            min="1"
            className="border p-2 w-full"
            value={currentDeployment.iterations}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                iterations: parseInt(e.target.value) || 1,
              })
            }
          />
        </div>
        {/* Deploy Only Checkbox */}
        <div className="flex items-center py-2 justify-between gap-2">
          <label
            htmlFor="deploy-only-checkbox"
            className="flex gap-2 items-center text-sm font-medium"
          >
            Deploy only <InfoIcon size={18} />
          </label>
          <input
            id="deploy-only-checkbox"
            type="checkbox"
            className="border w-5 h-5"
            checked={deployOnly}
            onChange={(e) => setDeployOnly(e.target.checked)}
          />
        </div>
        {/* Deploy Button */}
        <button
          className="rounded p-2 bg-blue-500 text-white hover:bg-blue-700"
          onClick={deploy}
          disabled={
            !currentDeployment.SutName || !currentDeployment.experimentName
          }
        >
          Deploy experiment
        </button>
      </div>
      <div>{ifDeploying && <LogsPanel ifDeploying={ifDeploying} />}</div>
    </div>
  );
};

export default ControlsPage;
