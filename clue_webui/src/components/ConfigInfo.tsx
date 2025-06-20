import {
  CalendarDotsIcon,
  FileIcon,
  FlaskIcon,
  LightningIcon,
  RepeatIcon,
  WrenchIcon,
} from "@phosphor-icons/react/dist/ssr";
import type {ResultEntry} from "../models/ResultEntry";

interface ConfigInfoProps {
  resultEntry: ResultEntry | null;
}

const ConfigInfo: React.FC<ConfigInfoProps> = ({resultEntry}) => {
  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  };

  const configItems = [
    {
      label: "Experiment ID",
      value: resultEntry ? resultEntry.id : "No data avaiable",
      icon: <FileIcon size={24} />,
    },
    {
      label: "SUT (System Under Test)",
      value: resultEntry ? "SUT Name" : "No data avaiable",
      icon: <WrenchIcon size={24} />,
    },
    {
      label: "Experiment",
      value: resultEntry ? resultEntry.branch_name : "No data avaiable",
      icon: <FlaskIcon size={24} />,
    },
    {
      label: "Workload Type",
      value: resultEntry ? resultEntry.workload : "No data avaiable",
      icon: <LightningIcon size={24} />,
    },
    {
      label: "Iterations",
      value: resultEntry
        ? resultEntry.iterations.toLocaleString()
        : "No data avaiable",
      icon: <RepeatIcon size={24} />,
    },
    {
      label: "Timestamp",
      value: resultEntry
        ? formatTimestamp(resultEntry.timestamp)
        : "No data avaiable",
      icon: <CalendarDotsIcon size={24} />,
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Content */}
      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {configItems.map((item, index) => (
            <div
              key={index}
              className="flex items-start gap-3 p-2 rounded-lg bg-gray-50 hover:bg-gray-100  transition-colors duration-200"
            >
              <span className="text-xl flex-shrink-0 mt-0.5">{item.icon}</span>
              <div className="min-w-0 flex-1">
                <dt className="text-sm font-medium text-gray-600 mb-1">
                  {item.label}
                </dt>
                <dd className="text-sm text-gray-900 font-mono bg-white px-2 py-1 rounded border">
                  {item.value}
                </dd>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ConfigInfo;
