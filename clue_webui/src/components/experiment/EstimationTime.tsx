import {useContext} from "react";
import {DeploymentContext} from "../../contexts/DeploymentContext";

const EstimationTime: React.FC = () => {
  const {currentDeployment} = useContext(DeploymentContext);

  const variantTotals = currentDeployment.variants.map((exp) => {
    const perIteration = currentDeployment.workloads.reduce(
      (sum, _w) => sum + 3,
      0
    );
    return {
      name: exp,
      perIteration,
      total: perIteration * currentDeployment.iterations,
    };
  });
  const overallTotal = variantTotals.reduce((sum, v) => sum + v.total, 0);

  return (
    <div className="h-full border-x border-t rounded shadow p-4 flex flex-col gap-2 md:w-1/5">
      <p className="font-medium">Estimated Benchmarking Time</p>
      {currentDeployment.deploy_only ? (
        <p className="text-sm text-amber-600">
          Benchmarking disabled - deploy only mode selected
        </p>
      ) : variantTotals.length === 0 ? (
        <p className="text-sm text-gray-500">
          Configure the experiment to see the total estimated benchmarking time
        </p>
      ) : (
        <div className="overflow-y-auto flex-1">
          {variantTotals.map((v) => (
            <div key={v.name} className="text-sm flex flex-col gap-1 mb-4">
              <p className="font-medium">Variant ({v.name})</p>
              {currentDeployment.workloads.map((w) => (
                <span key={w}>- Workload ({w}): 3 min</span>
              ))}
              <p>
                Total: {v.perIteration} min * {currentDeployment.iterations}{" "}
                iterations = {v.total} min
              </p>
            </div>
          ))}
        </div>
      )}
      {variantTotals.length > 0 && !currentDeployment.deploy_only && (
        <div className="mt-auto pt-2 border-t">
          <p className="font-medium">Total: {overallTotal} min</p>
        </div>
      )}
    </div>
  );
};

export default EstimationTime;
