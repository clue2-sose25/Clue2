import type {ResultDetails} from "../../models/ResultsDetails";
import ConfigCard from "./ConfigCard";

const ConfigsSection: React.FC<{data: ResultDetails}> = ({data}) => {
  return (
    <div className="mb-8">
      <div className="flex flex-col gap-1 pb-4">
        <div className="text-lg font-medium">Experiment Configs</div>
        <p className="text-xs text-gray-500">
          All configs and variables used for the deployment of the experiment.
        </p>
      </div>
      <ConfigCard
        title="Environment Config"
        data={data.configs.env_config}
        subtext={"The environment variables used during the experiment."}
      />
      <ConfigCard
        title="Clue Config"
        data={data.configs.clue_config}
        subtext={"The CLUE config file used during the experiment."}
      />
      <ConfigCard
        title="SUT Config"
        data={data.configs.sut_config}
        subtext={"The SUT config file used during the experiment."}
      />
    </div>
  );
};

export default ConfigsSection;
