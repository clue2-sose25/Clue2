import { useEffect, useState } from "react";
import type { Metric } from "../models/Metric";
import {
  ArrowLeftIcon,
  DownloadSimpleIcon,
  RepeatIcon,
} from "@phosphor-icons/react";
import { Link, useParams } from "react-router";
import type { ResultDetails } from "../models/ResultsDetails";
import ResultDetailsDisplay from "../components/results/ResultDetailsDisplay";

// Define params type for useParams
type ResultEntryParams = {
  uuid?: string;
};

const ResultPage = () => {
  // The ID of the results
  const { uuid } = useParams<ResultEntryParams>();

  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [resultDetails, setResultDetails] = useState<ResultDetails | null>(null);

  const handleResultsDownload = async (uuid: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = await fetch(`/api/results/${uuid}/download`);
      if (!res.ok) throw new Error("Failed to download");

      // Convert response to blob
      const blob = await res.blob();

      // Create download URL and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `results-${uuid}.zip`; // Set filename
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
    }
  };


  useEffect(() => {
    const fetchData = async () => {
      try {
        if (!uuid) {
          throw new Error("No result ID provided");
        }

        // Fetch ResultEntry data
        const resultRes = await fetch(`/api/results/${uuid}`);
        if (!resultRes.ok) {
          const errorData = await resultRes.json();
          throw new Error(errorData.detail || "Failed to fetch result");
        }
        const resultData: ResultDetails = await resultRes.json();
        setResultDetails(resultData);

        // const res = await fetch(`/api/results/assets/${uuid}`);
        // if (!res.ok) {
        //   const err = await res.json();
        //   throw new Error(err.detail || "Failed to load result assets");
        // }

        // const data = await res.json();

        // const entries = Object.entries(data.metrics) as [
        //   string,
        //   string | number | null | boolean
        // ][];
        // const metricsArr: Metric[] = entries.map(([label, value]) => ({
        //   label,
        //   value:
        //     typeof value === "number"
        //       ? Number(value.toFixed(2))
        //       : typeof value === "string"
        //         ? value
        //         : JSON.stringify(value),
        // }));
        // setMetrics(metricsArr);
        // setSvgData({
        //   cpu: data.cpu_svg,
        //   memory: data.memory_svg,
        //   wattage: data.wattage_svg,
        // });
      } catch (err) {
        console.error("Error fetching data:", err);
        setMetrics([]);
        setResultDetails(null);
      }
    };

    fetchData();
  }, [uuid]);

  // const [svgData, setSvgData] = useState<{
  //   cpu: string;
  //   memory: string;
  //   wattage: string;
  // } | null>(null);

  return (
    <div className="w-full h-full flex flex-col gap-6 p-6 pt-4">
      <div className="flex flex-col gap-4">

        {/* Top Bar with Back-Link and Buttons */}
        <div className="flex justify-between items-center">
          <Link
            to="/results"
            className="flex gap-2 items-center text-sm text-gray-600 hover:underline"
          >
            <ArrowLeftIcon /> Back
          </Link>
          <div className="flex gap-4">
            <button className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-200">
              <RepeatIcon size={20} /> Repeat benchmark
            </button>
            <button
              onClick={(e) => handleResultsDownload(uuid!, e)}
              className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-200"
            >
              <DownloadSimpleIcon size={20} /> Download results
            </button>
          </div>
        </div>

        {resultDetails && <ResultDetailsDisplay data={resultDetails} />}
      </div>
    </div>
  );
};

export default ResultPage;
