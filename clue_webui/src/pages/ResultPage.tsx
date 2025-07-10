import {useContext, useEffect, useState} from "react";
import {
  ArrowLeftIcon,
  DownloadSimpleIcon,
  RepeatIcon,
} from "@phosphor-icons/react";
import {Link, useNavigate, useParams} from "react-router";
import type {ResultDetails} from "../models/ResultsDetails";
import ResultDetailsDisplay from "../components/results/ResultDetailsDisplay";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {QueueContext} from "../contexts/QueueContext";

// Define params type for useParams
type ResultEntryParams = {
  uuid?: string;
};

const ResultPage = () => {
  // The ID of the results
  const {uuid} = useParams<ResultEntryParams>();

  const {setIfDeploying} = useContext(DeploymentContext);
  const {setCurrentQueue} = useContext(QueueContext);

  const navigate = useNavigate();

  const [resultDetails, setResultDetails] = useState<ResultDetails | null>(
    null
  );

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
      const link = document.createElement("a");
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

  const handleRepeatExperiment = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const response = await fetch("/api/deploy/sut", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          sut: resultDetails?.sut,
          variants: resultDetails?.variants
            .map((variant) => variant.name)
            .join(", "),
          workloads: resultDetails?.workloads
            .map((workload) => workload.name)
            .join(", "),
          n_iterations: resultDetails?.n_iterations,
          deploy_only: resultDetails?.deploy_only,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to repeat experiment");
      }
      // If you have these functions available, uncomment:
      setIfDeploying(true);
      fetchQueue();
      navigate("/dashboard");
    } catch (err) {
      console.error("Error repeating experiment:", err);
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
            <button
              onClick={(e) => {
                handleRepeatExperiment(e);
              }}
              className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-200"
            >
              <RepeatIcon size={20} /> Repeat experiment
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
