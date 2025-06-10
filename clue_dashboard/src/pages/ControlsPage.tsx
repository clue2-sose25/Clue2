import {useEffect, useState} from "react";
import type {Deployment} from "../models/Deployment";
import LogsPanel from "../components/LogsPanel";
import {InfoIcon} from "@phosphor-icons/react";

const workloadOptions = ["shaped", "rampup", "pausing", "fixed"];

const ControlsPage = () => {
  // Define the default deployment state with initial values
  const defaultDeployment: Deployment = {
    SUT: null,
    experiment: null,
    workload: "shaped", // Default workload
    iterations: 1, // Default iterations
  };

  const [currentDeployment, setCurrentDeployment] =
    useState<Deployment>(defaultDeployment);
  const [ifDeploying, setIfDeploying] = useState<boolean>(false);
  const [availableSUTs, setAvailableSUTs] = useState<string[]>([]);
  const [experiments, setExperiments] = useState<string[]>([]);
  const [deployOnly, setDeployOnly] = useState(false);

  // Fetch available SUTs and experiments on component mount
  useEffect(() => {
    fetch("/api/list/sut")
      .then((r) => r.json())
      .then((d) => setAvailableSUTs(d.suts ?? []))
      .catch(() => setAvailableSUTs([]));
    fetch("/api/list/experiments")
      .then((r) => r.json())
      .then((d) => setExperiments(d.experiments ?? []))
      .catch(() => setExperiments([]));
  }, []);

  // Deploy function to send deployment details to the API
  const deploy = async () => {
    if (!currentDeployment.SUT || !currentDeployment.experiment) return;
    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        sut_name: currentDeployment.SUT,
        experiment_name: currentDeployment.experiment,
      }),
    });
    setIfDeploying(true);
  };

  return (
    <div className="w-full h-full flex flex-col items-center gap-8 p-8">
      {/* Header texts */}
      <div className="flex flex-col items-center">
        <p className="text-xl font-medium">Deploy CLUE</p>
        <p className="">Choose your parameters for the benchmark</p>
      </div>
      {/* Parameters selection */}
      <div className="flex flex-col gap-4 w-1/3">
        {/* SUT Dropdown */}
        <div className="flex items-center justify-between gap-4">
          <label className="flex gap-2 items-center text-sm font-medium mb-1 ">
            SUT <InfoIcon size={18} />
          </label>
          <select
            className="border p-2 w-full"
            value={currentDeployment.SUT || ""}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                SUT: e.target.value,
              })
            }
          >
            <option value="" disabled>
              {availableSUTs.length > 0 ? "Select SUT" : "Loading SUTs..."}
            </option>
            {availableSUTs.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        {/* Experiment Dropdown */}
        <div className="flex items-center justify-between gap-4">
          <label className="flex gap-2 items-center text-sm font-medium mb-1">
            Experiment <InfoIcon size={18} />
          </label>
          <select
            className={`border py-2 px-4 w-full ${
              !currentDeployment.SUT ? "opacity-50" : ""
            }`}
            value={currentDeployment.experiment || ""}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                experiment: e.target.value,
              })
            }
            disabled={!currentDeployment.SUT}
          >
            <option value="" disabled>
              Select Experiment
            </option>
            {experiments.map((exp) => (
              <option key={exp} value={exp}>
                {exp}
              </option>
            ))}
          </select>
        </div>
        {/* Workload Type Dropdown */}
        <div className="flex items-center justify-between gap-4">
          <label className="flex gap-2 items-center text-sm font-medium mb-1 text-nowrap">
            Workload Type <InfoIcon size={18} />
          </label>
          <select
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
        <div className="flex items-center justify-between gap-4">
          <label className="flex gap-2 items-center text-sm font-medium mb-1 text-nowrap">
            Iterations <InfoIcon size={18} />
          </label>
          <input
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
        <div className="flex justify-between">
          <label className="inline-flex items-center gap-2">
            <p className="flex gap-2 items-center text-sm font-medium">
              Deploy only <InfoIcon size={18} />
            </p>
            <input
              type="checkbox"
              className="border w-4 h-4"
              checked={deployOnly}
              onChange={(e) => setDeployOnly(e.target.checked)}
            />
          </label>
        </div>

        {/* Deploy Button */}
        <button
          className="rounded p-2 bg-blue-500 text-white hover:bg-blue-700"
          onClick={deploy}
          disabled={!currentDeployment.SUT || !currentDeployment.experiment}
        >
          Deploy experiment
        </button>
      </div>
      <div>{ifDeploying && <LogsPanel ifDeploying={ifDeploying} />}</div>
    </div>
  );
};

export default ControlsPage;
