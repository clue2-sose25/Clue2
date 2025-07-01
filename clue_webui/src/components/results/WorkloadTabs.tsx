import { useState } from "react";
import type { Variant, Workload } from "../../models/ResultsDetails";

const WorkloadTabs: React.FC<{
  workloads: Workload[];
  variants: Variant[];
}> = ({ workloads, variants }) => {
  const [activeTab, setActiveTab] = useState(0);

  if (workloads.length === 0) return null;

  return (
    <div className="mb-8">
      <div className="flex flex-col gap-1 pb-4">
        <div className="text-lg font-medium">Workloads</div>
        <p className="text-xs text-gray-500">
          A list of workloads and variants selected for the experiment. Open a
          workload tab to see the deployed variants.
        </p>
      </div>

      {/* Tab Headers */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {workloads.map((workload, index) => (
            <button
              key={index}
              onClick={() => setActiveTab(index)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === index
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {workload.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-4">
        {workloads.map((workload, index) => (
          <div key={index} className={activeTab === index ? "block" : "hidden"}>
            <div className="bg-white border rounded-lg p-4 space-y-4">
              <div className="flex flex-col gap-1">
                <div className="text-lg font-medium">
                  Workload: {workload.name}
                </div>
                <p className="text-xs text-gray-500">{workload.description}</p>
              </div>
              <div>
                <div className="block mb-2">
                  <strong>Timeout Duration: </strong>
                  {workload.timeout_duration} seconds
                </div>
              </div>

              <div>
                <strong className="block mb-2">Workload Settings:</strong>
                <pre className="bg-gray-50 p-3 rounded text-sm overflow-auto">
                  {JSON.stringify(workload.workload_settings, null, 2)}
                </pre>
              </div>
              <div>
                <strong className="block mb-3">Variants:</strong>
                <div className="space-y-3">
                  {variants.map((variant, vIdx) => (
                    <div
                      key={vIdx}
                      className="border border-gray-200 rounded p-3"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium">{variant.name}</h4>
                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          {variant.target_branch}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        {variant.description}
                      </p>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <strong>Autoscaling:</strong> {variant.autoscaling}
                        </div>
                        <div>
                          <strong>Max Autoscale:</strong>{" "}
                          {variant.max_autoscale}
                        </div>
                        <div>
                          <strong>Colocated Workload:</strong>{" "}
                          {variant.colocated_workload ? "Yes" : "No"}
                        </div>
                      </div>
                      <div className="mt-2">
                        <strong className="text-sm">Critical Services:</strong>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {variant.critical_services.map((service, sIdx) => (
                            <span
                              key={sIdx}
                              className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                            >
                              {service}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkloadTabs;
