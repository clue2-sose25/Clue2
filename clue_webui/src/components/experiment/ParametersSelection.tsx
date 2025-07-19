import {useRef, useEffect, useState, useContext} from "react";
import {PlusCircleIcon} from "@phosphor-icons/react";
import {IconButton, Tooltip} from "@mui/material";
import {Link} from "react-router";
import {DeploymentContext} from "../../contexts/DeploymentContext";
import type {SUT} from "../../models/SUT";

const ParametersSelection: React.FC = () => {
  const {currentDeployment, setCurrentDeployment} =
    useContext(DeploymentContext);
  const [availableSUTs, setAvailableSUTs] = useState<SUT[]>([]);
  const variantSelectAllRef = useRef<HTMLInputElement>(null);
  const workloadSelectAllRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/api/suts")
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`API responded with status ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setAvailableSUTs(data ?? []);
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
    .flatMap((sut) => sut.workloads);

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

  return (
    <div
      className="h-full overflow-y-auto flex flex-col gap-4 border-x border-t rounded shadow p-4 md:w-2/5 w-3/4 flex-grow"
      style={{scrollBehavior: "smooth", willChange: "scroll-position"}}
    >
      {/* SUT Dropdown */}
      <div className="flex flex-col gap-2">
        <label
          htmlFor="sut-select"
          className="flex flex-col gap-2 text-sm font-medium"
        >
          <div className="flex justify-start w-full items-center">
            <span>System Under Test (SUT)</span>
            <Tooltip title="Add a custom SUT config" arrow placement="top">
              <IconButton component={Link} to="/experiment/add-sut">
                <PlusCircleIcon size={20} />
              </IconButton>
            </Tooltip>
          </div>
          <p className="text-xs text-gray-500">
            Select the SUT config to deploy. To deploy a custom SUT config,
            click the plus button.
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
        <label className="flex flex-col gap-2 text-sm font-medium">
          <div className="flex justify-start w-full gap-2 items-center">
            Variants
          </div>
          <p className="text-xs text-gray-500">
            A list of possible SUT variants, corresponding to specific GIT
            branches. You can select multiple variants; they will run
            sequentially.
          </p>
        </label>
        <div
          className={`border p-2 flex flex-col gap-2 max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 ${
            !currentDeployment.sut ? "opacity-50" : ""
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
                    checked={currentDeployment.variants.includes(variant.name)}
                    onChange={() => {
                      const exists = currentDeployment.variants.includes(
                        variant.name
                      );
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
        <label className="flex flex-col gap-2 text-sm font-medium">
          <div className="flex justify-start w-full gap-2 items-center">
            Workloads
          </div>
          <p className="text-xs text-gray-500">
            A list of possible workload types. You can select multiple
            workloads; they will run sequentially.
          </p>
          {currentDeployment.deploy_only && (
            <p className="text-xs text-amber-600 font-medium">
              Workload generator will not start due to "Deploy only" option
              being selected.
            </p>
          )}
        </label>
        <div
          className={`border p-2 flex flex-col gap-2 max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100 ${
            !currentDeployment.sut || currentDeployment.deploy_only
              ? "opacity-50"
              : ""
          }`}
        >
          <label className="flex gap-2 items-center font-medium">
            <input
              type="checkbox"
              ref={workloadSelectAllRef}
              className="mt-1 bg-white"
              disabled={!currentDeployment.sut || currentDeployment.deploy_only}
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
                    disabled={
                      !currentDeployment.sut || currentDeployment.deploy_only
                    }
                    checked={currentDeployment.workloads.includes(w.name)}
                    onChange={() => {
                      const exists = currentDeployment.workloads.includes(
                        w.name
                      );
                      setCurrentDeployment({
                        ...currentDeployment,
                        workloads: exists
                          ? currentDeployment.workloads.filter(
                              (n) => n !== w.name
                            )
                          : [...currentDeployment.workloads, w.name],
                      });
                    }}
                  />
                  <span>{w.name}</span>
                </div>
                <div className="flex flex-col">
                  {w.description && (
                    <span className="text-xs text-gray-500">
                      {w.description}
                    </span>
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
        <label className="flex flex-col gap-2 text-sm font-medium">
          <div className="flex justify-start w-full gap-2 items-center">
            Number of iterations
          </div>
          <p className="text-xs text-gray-500">
            The number of iterations for each of the runs (variant + workload);
            more iterations the consistency of the results metrics.
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
      <div className="flex items-center py-2 justify-between gap-2">
        <label className="flex flex-col gap-2 text-sm font-medium">
          <div className="flex justify-start w-full gap-2 items-center">
            Deploy only
          </div>
          <p className="text-xs text-gray-500">
            If selected the SUT will be deployed without running the actual
            benchmark. For testing purposes.
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
              workloads: e.target.checked ? [] : currentDeployment.workloads,
            })
          }
        />
      </div>
    </div>
  );
};

export default ParametersSelection;
