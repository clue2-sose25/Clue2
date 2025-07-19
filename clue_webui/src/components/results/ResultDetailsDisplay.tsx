import type {ResultDetails} from "../../models/ResultsDetails";
import ConfigsSection from "./ConfigsSection";
import ParametersSection from "./ParametersSection";

const ResultDetailsDisplay: React.FC<{data: ResultDetails}> = ({data}) => {
  return (
    <div className="w-full mx-auto">
      <div className="flex gap-8 w-full">
        <div className="w-1/2">
          <ParametersSection data={data} />
        </div>
        <div className="w-1/2">
          <ConfigsSection data={data} />
        </div>
      </div>
      {/* <ResultsSection workloads={data.workloads} variants={data.variants} /> */}
    </div>
  );
};

export default ResultDetailsDisplay;
