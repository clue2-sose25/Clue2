import type { ResultDetails } from "../../models/ResultsDetails";
import ConfigSection from "./ConfigSection";
import WorkloadTabs from "./WorkloadTabs";

const ResultDetailsDisplay: React.FC<{ data: ResultDetails }> = ({ data }) => {
    return (
        <div className="w-full mx-auto">
            <div className="text-lg font-medium py-2">Experiment Information</div>

            {/* Basic Info */}
            <div className="mb-8">
                <div className="bg-white border rounded-sm p-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div><strong>Experiment ID:</strong> <span className="font-mono text-sm">{data.id}</span></div>
                        <div><strong>SUT:</strong> {data.sut}</div>
                        <div><strong>Status:</strong>
                            <span className={`ml-2 px-2 py-1 rounded text-sm font-medium ${data.status === 'STARTED' ? 'bg-green-100 text-green-800' :
                                data.status === 'COMPLETED' ? 'bg-blue-100 text-blue-800' :
                                    data.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                                        'bg-gray-100 text-gray-800'
                                }`}>
                                {data.status}
                            </span>
                        </div>
                        <div><strong>Timestamp:</strong> {data.timestamp}</div>
                        <div><strong>Iterations:</strong> {data.n_iterations}</div>
                        <div><strong>Deploy Only:</strong> {data.deploy_only ? 'Yes' : 'No'}</div>
                    </div>
                </div>
            </div>

            {/* Collapsible Configs */}
            <div className="mb-8">
                <h2 className="text-lg font-medium py-2">Configuration</h2>
                <ConfigSection title="Environment Config" data={data.configs.env_config} />
                <ConfigSection title="Clue Config" data={data.configs.clue_config} />
                <ConfigSection title="SUT Config" data={data.configs.sut_config} />
            </div>

            {/* Workload Tabs */}
            <WorkloadTabs workloads={data.workloads} variants={data.variants} />
        </div>
    );
};

export default ResultDetailsDisplay;