import {useContext, useEffect, useState} from "react";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {InfoIcon, RocketLaunchIcon, StackPlusIcon} from "@phosphor-icons/react";
import type {SUT} from "../models/SUT";
import {Tooltip} from "@mui/material";
import {workloadOptions, type Workload} from "../models/DeploymentForm";
import {useNavigate} from "react-router";
import {QueueContext} from "../contexts/QueueContext";

const ControlsPage = () => {
  const {currentDeployment, setCurrentDeployment, setIfDeploying} =
    useContext(DeploymentContext);

  const {currentQueue, setCurrentQueue} = useContext(QueueContext);

  const navigate = useNavigate();
  const [availableSUTs, setAvailableSUTs] = useState<SUT[]>([]);

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

  useEffect(() => {
    fetch("/api/suts")
      .then(async (r) => {
        if (!r.ok) {
          throw new Error(`API responded with status ${r.status}`);
        }
        const data = await r.json();
        return data;
      })
      .then((d) => setAvailableSUTs(d.suts ?? []))
      .catch((err) => {
        console.error("Failed to fetch SUTs:", err);
        setAvailableSUTs([]);
      });
  }, []);

  const deploySUT = async () => {
    if (
      !currentDeployment.SutName ||
      currentDeployment.experimentNames.length === 0
    )
      return;

    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        sut_name: currentDeployment.SutName,
        experiment_name: currentDeployment.experimentNames.join(","),
        n_iterations: currentDeployment.iterations,
        deploy_only: currentDeployment.deploy_only,
      }),
    });

    setIfDeploying(true);
    fetchQueue();
    navigate("/dashboard");
  };

  return (
    <div className="w-full h-full flex flex-col items-center gap-6 pt-4">
      <div className="flex flex-col items-center">
        <p className="text-xl font-medium">Deploy CLUE</p>
        <p>Choose your parameters for the benchmark</p>
      </div>

      <div className="flex flex-col gap-4 md:w-1/3 w-3/4">
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
                experimentNames: [],
              });
            }}
          >
            <option value="" disabled>
              {availableSUTs.length > 0 ? "Select the SUT" : "Loading SUTs..."}
            </option>
            {availableSUTs.map((sut) => (
              <option key={sut.name} value={sut.name}>
                {sut.name}
              </option>
            ))}
          </select>
        </div>

        {/* Experiment Selection */}
        <div className="flex flex-col gap-2">
          <label className="flex flex-col gap-2  text-sm font-medium">
            <div className="flex justify-start w-full gap-2 items-center">
              Experiments
              <Tooltip
                title="Select one or more experiments to run sequentially"
                placement="right"
                arrow
              >
                <InfoIcon size={18} />
              </Tooltip>
            </div>
            <p className="text-xs text-gray-500">
              You can select multiple experiments; they will run sequentially.
            </p>
          </label>
          <div
            className={`border p-2 flex flex-col gap-2 max-h-[10.5rem] overflow-auto  ${
              !currentDeployment.SutName ? "opacity-50" : ""
            }`}
          >
            {availableSUTs
              .filter((sut) => sut.name === currentDeployment.SutName)
              .flatMap((sut) => sut.experiments)
              .map((exp) => (
                <label
                  key={exp.name}
                  className="flex flex-col gap-1 items-start"
                >
                  <div className="flex gap-2">
                    <input
                      type="checkbox"
                      className="mt-1"
                      disabled={!currentDeployment.SutName}
                      checked={currentDeployment.experimentNames.includes(
                        exp.name
                      )}
                      onChange={() => {
                        const exists =
                          currentDeployment.experimentNames.includes(exp.name);
                        setCurrentDeployment({
                          ...currentDeployment,
                          experimentNames: exists
                            ? currentDeployment.experimentNames.filter(
                                (n) => n !== exp.name
                              )
                            : [...currentDeployment.experimentNames, exp.name],
                        });
                      }}
                    />
                    <span>{exp.name}</span>
                  </div>

                  <div className="flex flex-col">
                    {exp.description && (
                      <span className="text-xs text-gray-500">
                        {exp.description}
                      </span>
                    )}
                  </div>
                </label>
              ))}
            {availableSUTs
              .filter((sut) => sut.name === currentDeployment.SutName)
              .flatMap((sut) => sut.experiments).length === 0 && (
              <p>Select experiments</p>
            )}
          </div>
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
          className={`rounded p-2  ${
            !currentDeployment.SutName ||
            currentDeployment.experimentNames.length === 0
              ? "bg-gray-300 text-gray-500"
              : "bg-blue-500 text-white hover:bg-blue-700"
          }`}
          onClick={deploySUT}
          disabled={
            !currentDeployment.SutName ||
            currentDeployment.experimentNames.length === 0
          }
        >
          {currentQueue ? (
            <div className="flex items-center justify-center gap-2">
              <RocketLaunchIcon size={24} className="inline-block" />
              <span className="font-medium">Deploy experiment</span>
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

export default ControlsPage;
