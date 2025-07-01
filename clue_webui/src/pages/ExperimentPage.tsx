import { useContext, useEffect, useState, useRef } from "react";
import { DeploymentContext } from "../contexts/DeploymentContext";
import { PlusCircleIcon, RocketLaunchIcon, StackPlusIcon } from "@phosphor-icons/react";
import type { SUT } from "../models/SUT";
import { IconButton, Tooltip } from "@mui/material";
import { useNavigate } from "react-router";
import { QueueContext } from "../contexts/QueueContext";

const ExperimentPage = () => {
  const { currentDeployment, setCurrentDeployment, setIfDeploying } =
    useContext(DeploymentContext);

  const { currentQueue, setCurrentQueue } = useContext(QueueContext);

  const navigate = useNavigate();
  const [availableSUTs, setAvailableSUTs] = useState<SUT[]>([]);
  const variantSelectAllRef = useRef<HTMLInputElement>(null);
  const workloadSelectAllRef = useRef<HTMLInputElement>(null);

  // System Under Test - Progress
  const sutConfigProgress = !!currentDeployment.sut && currentDeployment.variants.length > 0 && currentDeployment.workloads.length > 0


  const benchmarkingConfigProgress =
    currentDeployment.iterations > 0;
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

  useEffect(() => {
    fetch("/api/suts")
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`API responded with status ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        console.log(data)
        setAvailableSUTs(data ?? [])
      })
      .catch((err) => {
        console.error("Failed to fetch SUTs:", err);
        setAvailableSUTs([]);
      });
  }, []);

  const variantsOptions = availableSUTs
    .filter((sut) => sut.name === currentDeployment.sut)
    .flatMap((sut) => sut.variants);

  const workloadOptions = availableSUTs
    .filter((sut) => sut.name === currentDeployment.sut)
    .flatMap((sut) => sut.workloads)

  const allVariantsSelected =
    variantsOptions.length > 0 &&
    currentDeployment.variants.length === variantsOptions.length;
  const someVariantsSelected =
    currentDeployment.variants.length > 0 && !allVariantsSelected;

  const allWorkloadsSelected =
    currentDeployment.workloads.length === workloadOptions.length;
  const someWorkloadsSelected =
    currentDeployment.workloads.length > 0 && !allWorkloadsSelected;

  useEffect(() => {
    if (variantSelectAllRef.current) {
      variantSelectAllRef.current.indeterminate = someVariantsSelected;
    }
  }, [someVariantsSelected]);

  useEffect(() => {
    if (workloadSelectAllRef.current) {
      workloadSelectAllRef.current.indeterminate = someWorkloadsSelected;
    }
  }, [someWorkloadsSelected]);

  const workloadTime = () => 3;
  const variantTotals = currentDeployment.variants.map((exp) => {
    const perIteration = currentDeployment.workloads.reduce(
      (sum, w) => sum + 3,
      0
    );
    return {
      name: exp,
      perIteration,
      total: perIteration * currentDeployment.iterations,
    };
  });
  const overallTotal = variantTotals.reduce((sum, v) => sum + v.total, 0);

  const deploySUT = async () => {
    if (!deployEnabled) return;

    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
    <div className="w-full h-full flex flex-col items-center ">
      <div className="h-[calc(100%-3.5rem)] flex flex-col md:flex-row gap-4 w-full justify-center">
        {/* Progress Sidebar */}
        <div className="h-full border-x border-t rounded shadow p-4 flex flex-col gap-2 md:w-1/5">
          <p className="font-medium">Configuration Progress</p>
          <label className="flex gap-2 items-center">
            <input type="checkbox" readOnly checked={sutConfigProgress} className="w-5 h-5" />
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

        {/* Parameter Selection */}
        <div className="h-full overflow-y-auto flex flex-col gap-4 border-x border-t rounded shadow p-4 md:w-2/5 w-3/4 flex-grow">
          {/* SUT Dropdown */}
          <div className="flex flex-col gap-2">
            <label
              htmlFor="sut-select"
              className="flex flex-col gap-2  text-sm font-medium"
            >
              <div className="flex justify-start w-full items-center">
                <span>System Under Test (SUT)</span>
                <Tooltip title="Add a custom SUT config" arrow placement="top" >
                  <IconButton>
                    <PlusCircleIcon size={20} />
                  </IconButton>
                </Tooltip>
              </div>
              <p className="text-xs text-gray-500">
                Select the SUT config to deploy. To deploy a custom SUT config, click the plus button.
              </p>
            </label>
            <select
              id="sut-select"
              className="border p-2 w-full"
              value={currentDeployment.sut || ""}
              onChange={(e) => {
                setCurrentDeployment({
                  ...currentDeployment,
                  sut: e.target.value,
                  variants: [],
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

          {/* Variant Selection */}
          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-2  text-sm font-medium">
              <div className="flex justify-start w-full gap-2 items-center">
                Variants
              </div>
              <p className="text-xs text-gray-500">
                A list of possible SUT variants, corresponding to specific GIT branches. You can select multiple variants; they will run sequentially.
              </p>
            </label>
            <div
              className={`border p-2 flex flex-col gap-2 max-h-[10.5rem] overflow-auto  ${!currentDeployment.sut ? "opacity-50" : ""
                }`}
            >
              <label className="flex gap-2 items-center font-medium">
                <input
                  type="checkbox"
                  ref={variantSelectAllRef}
                  className="mt-1 bg-white"
                  disabled={!currentDeployment.sut}
                  checked={allVariantsSelected}
                  onChange={(e) => {
                    setCurrentDeployment({
                      ...currentDeployment,
                      variants: e.target.checked
                        ? variantsOptions.map((variant) => variant.name)
                        : [],
                    });
                  }}
                />
                Select all
              </label>
              {availableSUTs
                .filter((sut) => sut.name === currentDeployment.sut)
                .flatMap((sut) => sut.variants)
                .map((variant) => (
                  <label
                    key={variant.name}
                    className="flex flex-col gap-1 items-start"
                  >
                    <div className="flex gap-2">
                      <input
                        type="checkbox"
                        className="mt-1 bg-white"
                        disabled={!currentDeployment.sut}
                        checked={currentDeployment.variants.includes(
                          variant.name
                        )}
                        onChange={() => {
                          const exists =
                            currentDeployment.variants.includes(variant.name);
                          setCurrentDeployment({
                            ...currentDeployment,
                            variants: exists
                              ? currentDeployment.variants.filter(
                                (n) => n !== variant.name
                              )
                              : [...currentDeployment.variants, variant.name],
                          });
                        }}
                      />
                      <span>{variant.name}</span>
                    </div>

                    <div className="flex flex-col">
                      {variant.description && (
                        <span className="text-xs text-gray-500">
                          {variant.description}
                        </span>
                      )}
                    </div>
                  </label>
                ))}
              {availableSUTs
                .filter((sut) => sut.name === currentDeployment.sut)
                .flatMap((sut) => sut.variants).length === 0 && (
                  <p>Firstly select the SUT</p>
                )}
            </div>
          </div>

          {/* Workload Selection */}
          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-2  text-sm font-medium">
              <div className="flex justify-start w-full gap-2 items-center">
                Workloads
              </div>
              <p className="text-xs text-gray-500">
                A list of possible workload types. You can select multiple workloads; they will run sequentially.
              </p>
            </label>
            <div
              className={`border p-2 flex flex-col gap-2 max-h-[10.5rem] overflow-auto  ${!currentDeployment.sut ? "opacity-50" : ""
                }`}
            >
              <label className="flex gap-2 items-center font-medium">
                <input
                  type="checkbox"
                  ref={workloadSelectAllRef}
                  className="mt-1 bg-white"
                  disabled={!currentDeployment.sut}
                  checked={allWorkloadsSelected}
                  onChange={(e) => {
                    setCurrentDeployment({
                      ...currentDeployment,
                      workloads: e.target.checked
                        ? workloadOptions.map((w) => w.name)
                        : [],
                    });
                  }}
                />
                Select all
              </label>
              {availableSUTs
                .filter((sut) => sut.name === currentDeployment.sut)
                .flatMap((sut) => sut.workloads)
                .map((w) => (
                  <label key={w.name} className="flex flex-col gap-1 items-start">
                    <div className="flex gap-2">
                      <input
                        type="checkbox"
                        className="mt-1 bg-white"
                        disabled={!currentDeployment.sut}
                        checked={currentDeployment.workloads.includes(w.name)}
                        onChange={() => {
                          const exists = currentDeployment.workloads.includes(w.name);
                          setCurrentDeployment({
                            ...currentDeployment,
                            workloads: exists
                              ? currentDeployment.workloads.filter((n) => n !== w.name)
                              : [...currentDeployment.workloads, w.name],
                          });
                        }}
                      />
                      <span>{w.name}</span>
                    </div>
                    <div className="flex flex-col">
                      {w.description && (
                        <span className="text-xs text-gray-500">{w.description}</span>
                      )}
                    </div>
                  </label>
                ))}
              {availableSUTs
                .filter((sut) => sut.name === currentDeployment.sut)
                .flatMap((sut) => sut.workloads).length === 0 && (
                  <p>Firstly select the SUT</p>
                )}
            </div>
          </div>

          {/* Iterations Input */}
          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-2  text-sm font-medium">
              <div className="flex justify-start w-full gap-2 items-center">
                Number of iterations
              </div>
              <p className="text-xs text-gray-500">
                The number of iterations for each of the runs (variant + workload); more iterations the consistency of the results metrics.
              </p>
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
          <div className="flex items-center py-2 justify-between gap-2 ">
            <label className="flex flex-col gap-2 text-sm font-medium">
              <div className="flex justify-start w-full gap-2 items-center">
                Deploy only
              </div>
              <p className="text-xs text-gray-500">
                If selected the SUT will be deployed without running the actual benchmark. For testing purposes.
              </p>
            </label>
            <input
              id="deploy-only-checkbox"
              type="checkbox"
              className="border w-6 h-6 bg-white"
              checked={currentDeployment.deploy_only}
              onChange={(e) =>
                setCurrentDeployment({
                  ...currentDeployment,
                  deploy_only: e.target.checked,
                })
              }
            />
          </div>
        </div>

        {/* Estimated Benchmarking Time */}
        <div className="h-full border-x border-t rounded shadow p-4 flex flex-col gap-2 md:w-1/5">
          <p className="font-medium">Estimated Benchmarking Time</p>
          {variantTotals.length === 0 ? (
            <p className="text-sm text-gray-500">Configure the experiment to see the total estimated benchmarking time</p>
          ) : (
            variantTotals.map((v) => (
              <div key={v.name} className="text-sm flex flex-col gap-1">
                <p className="font-medium">Variant ({v.name})</p>
                {currentDeployment.workloads.map((w) => (
                  <span key={w}>- Workload ({w}): 3 min</span>
                ))}
                <p>
                  Total: {v.perIteration} min * {currentDeployment.iterations} iterations ={' '}
                  {v.total} min
                </p>
              </div>
            ))
          )}
          {variantTotals.length > 0 && (
            <p className="font-medium pt-2">Total: {overallTotal} min</p>
          )}
        </div>
      </div >
      <div className="flex w-full justify-start h-[3.5rem] p-2 border rounded shadow gap-2">{/* Deploy Button */}
        <div className="h-full p-4 flex flex-col gap-2 md:w-1/5"></div>
        <button
          className={` rounded py-2 px-4  ${!deployEnabled
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
    </div >
  );
};

export default ExperimentPage;
