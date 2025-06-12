import {useContext, useEffect, useState} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {InfoIcon, RocketLaunchIcon} from "@phosphor-icons/react";
import type {SUT} from "../models/SUT";
import {Tooltip} from "@mui/material";
import {workloadOptions, type Workload} from "../models/DeploymentForm";
import {useNavigate} from "react-router";

const ControlsPage = () => {
  const {currentDeployment, setCurrentDeployment, setIfDeploying} =
    useContext(DeploymentContext);

  const navigate = useNavigate();
  const [availableSUTs, setAvailableSUTs] = useState<SUT[]>([]);

  useEffect(() => {
    fetch("/api/list/sut")
      .then((r) => r.json())
      .then((d) => setAvailableSUTs(d.suts ?? []))
      .catch(() => setAvailableSUTs([]));
  }, []);

  const deploySUT = async () => {
    if (!currentDeployment.SutName || !currentDeployment.experimentName) return;

    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        sut_name: currentDeployment.SutName,
        experiment_name: currentDeployment.experimentName,
        n_iterations: currentDeployment.iterations,
        deploy_only: currentDeployment.deploy_only,
      }),
    });

    setIfDeploying(true);
    navigate("/dashboard");
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
            SUT
            <Tooltip
              title="The selected System Under Test to deploy"
              placement="right"
              arrow
            >
              <InfoIcon size={18} />
            </Tooltip>
          </label>
          <select
            id="sut-select"
            className="border p-2 w-full"
            value={currentDeployment.SutName || ""}
            onChange={(e) => {
              setCurrentDeployment({
                ...currentDeployment,
                SutName: e.target.value,
                experimentName: null,
              });
            }}
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
            Experiment
            <Tooltip
              title="The SUT experiment to deploy"
              placement="right"
              arrow
            >
              <InfoIcon size={18} />
            </Tooltip>
          </label>
          <select
            id="experiment-select"
            className={`border py-2 px-4 w-full ${
              !currentDeployment.SutName ? "opacity-50" : ""
            }`}
            value={currentDeployment.experimentName || ""}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                experimentName: e.target.value,
              })
            }
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
            className="flex gap-2 items-center text-sm font-medium"
          >
            Workload Type
            <Tooltip
              title="The type of the workload which will be used during the experiment"
              placement="right"
              arrow
            >
              <InfoIcon size={18} />
            </Tooltip>
          </label>
          <select
            id="workload-select"
            className="border p-2 w-full"
            value={currentDeployment.workload ?? ""}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                workload: e.target.value as Workload,
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
            className="flex gap-2 items-center text-sm font-medium"
          >
            Iterations
            <Tooltip
              title="The number of iterations for the experiment"
              placement="right"
              arrow
            >
              <InfoIcon size={18} />
            </Tooltip>
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
            Deploy only
            <Tooltip
              title="If selected the SUT will be deployed without running the actual benchmark. For testing purposes."
              placement="right"
              arrow
            >
              <InfoIcon size={18} />
            </Tooltip>
          </label>
          <input
            id="deploy-only-checkbox"
            type="checkbox"
            className="border w-5 h-5"
            checked={currentDeployment.deploy_only}
            onChange={(e) =>
              setCurrentDeployment({
                ...currentDeployment,
                deploy_only: e.target.checked,
              })
            }
          />
        </div>

        {/* Deploy Button */}
        <button
          className="rounded p-2 bg-blue-500 text-white hover:bg-blue-700"
          onClick={deploySUT}
          disabled={
            !currentDeployment.SutName || !currentDeployment.experimentName
          }
        >
          <div className="flex items-center justify-center gap-2">
            <RocketLaunchIcon size={24} className="inline-block" />
            <span className="font-medium">Deploy experiment</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default ControlsPage;
