import type {ResultDetails} from "../../models/ResultsDetails";

const ParametersSection: React.FC<{data: ResultDetails}> = ({data}) => {
  return (
    <div>
      <div className="flex flex-col gap-1 pb-4">
        <div className="text-lg font-medium">Experiment Parameters</div>
        <p className="text-xs text-gray-500">
          The selected parameters and basic information about the execution of
          the experiment.
        </p>
      </div>
      {/* Basic Info */}
      <div className="mb-8">
        <div className="bg-white border rounded-sm p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <strong>Experiment ID:</strong>{" "}
              <span className="font-mono text-sm">{data.id}</span>
            </div>
            <div>
              <strong>SUT:</strong> {data.sut}
            </div>
            <div>
              <strong>Variants:</strong>{" "}
              {data.variants.map((variant) => variant.name).join(", ")}
            </div>
            <div>
              <strong>Workloads:</strong>{" "}
              {data.workloads.map((workload) => workload.name).join(", ")}
            </div>
            <div>
              <strong>Status:</strong>
              <span
                className={`ml-2 px-2 py-1 rounded text-sm font-medium ${
                  data.status === "STARTED"
                    ? "bg-green-100 text-green-800"
                    : data.status === "COMPLETED"
                    ? "bg-blue-100 text-blue-800"
                    : data.status === "FAILED"
                    ? "bg-red-100 text-red-800"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                {data.status}
              </span>
            </div>
            <div>
              <strong>Timestamp:</strong> {data.timestamp}
            </div>
            <div>
              <strong>Iterations:</strong> {data.n_iterations}
            </div>
            <div>
              <strong>Deploy Only:</strong> {data.deploy_only ? "Yes" : "No"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParametersSection;
