import {Fragment, useEffect, useState} from "react";
import type {Metric} from "../models/Metric";
import {
  ArrowLeftIcon,
  DownloadSimpleIcon,
  FilesIcon,
  GearIcon,
  RepeatIcon,
} from "@phosphor-icons/react";
import {Link, useParams} from "react-router";
import type {ResultEntry} from "../models/ResultEntry";
import ConfigInfo from "../components/ConfigInfo";

// Define params type for useParams
type ResultEntryParams = {
  resultEntryId?: string;
};

const ResultPage = () => {
  // The ID of the results
  const {resultEntryId} = useParams<ResultEntryParams>();

  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [resultEntry, setResultEntry] = useState<ResultEntry | null>(null);
  const [loading, setLoading] = useState(true);

  const handleDownloadButton = async () => {
    try {
      // Extract just the timestamp from resultEntryId (assumes timestamp is first two parts)
      if (!resultEntryId) {
        return;
      }
      const parts = resultEntryId.split("_");
      if (parts.length < 2) {
        throw new Error("Invalid resultEntryId format");
      }
      const timestamp = `${parts[0]}_${parts[1]}`;

      const response = await fetch(`/api/results/${timestamp}/download`);

      if (!response.ok) {
        throw new Error(`Error downloading file: ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;

      // Extract filename from headers, or use a fallback
      const disposition = response.headers.get("Content-Disposition");
      const match = disposition?.match(/filename="?(.+)"?/);
      const filename = match?.[1] || "download.zip";

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);

      try {
        if (!resultEntryId) {
          throw new Error("No result ID provided");
        }

        // Fetch ResultEntry data
        const resultRes = await fetch(`/api/results/${resultEntryId}`);
        if (!resultRes.ok) {
          const errorData = await resultRes.json();
          throw new Error(errorData.detail || "Failed to fetch result");
        }
        const resultData: ResultEntry = await resultRes.json();
        setResultEntry(resultData);

        const res = await fetch(`/api/results/assets/${resultEntryId}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to load result assets");
        }

        const data = await res.json();

        const entries = Object.entries(data.metrics) as [
          string,
          string | number | null | boolean
        ][];
        const metricsArr: Metric[] = entries.map(([label, value]) => ({
          label,
          value:
            typeof value === "number"
              ? Number(value.toFixed(2))
              : typeof value === "string"
              ? value
              : JSON.stringify(value),
        }));
        setMetrics(metricsArr);
        setSvgData({
          cpu: data.cpu_svg,
          memory: data.memory_svg,
          wattage: data.wattage_svg,
        });
      } catch (err) {
        console.error("Error fetching data:", err);
        setMetrics([]);
        setResultEntry(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [resultEntryId]);

  const [svgData, setSvgData] = useState<{
    cpu: string;
    memory: string;
    wattage: string;
  } | null>(null);

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Top Bar with Back-Link and Buttons */}
      <div className="flex flex-col gap-4">
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
              onClick={handleDownloadButton}
              className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-200"
            >
              <DownloadSimpleIcon size={20} /> Download results
            </button>
          </div>
        </div>

        {/* Configuration Details */}
        <div className="flex flex-col gap-4">
          <div className="flex gap-2 items-center">
            <GearIcon size="24" />
            <p className="text-xl font-medium">Experiment Config</p>
          </div>
          <ConfigInfo resultEntry={resultEntry} />
        </div>

        {/* Results Summary */}
        <div className="flex flex-col gap-4">
          <div className="flex gap-2 items-center">
            <FilesIcon size="24" />
            <p className="text-xl font-medium">Results summary</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {metrics.length > 0 ? (
              metrics.map((m) => (
                <div
                  key={m.label}
                  className="border rounded-xl shadow bg-white py-1 px-3"
                >
                  <span className="text-sm">{m.label}: </span>
                  <span className="text-md font-bold text-center">
                    {m.value}
                  </span>
                </div>
              ))
            ) : (
              <div>
                No metrics available. Did the experiment finish running?
              </div>
            )}
          </div>
          <div className="w-full max-w-full grid grid-cols-1 md:grid-cols-3 gap-4">
            {svgData && (
              <Fragment>
                <div
                  className="w-32 h-32"
                  dangerouslySetInnerHTML={{__html: svgData.cpu}}
                />
                <div
                  className="w-32 h-32"
                  dangerouslySetInnerHTML={{__html: svgData.memory}}
                />
                <div
                  className="w-32 h-32"
                  dangerouslySetInnerHTML={{__html: svgData.wattage}}
                />
              </Fragment>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultPage;
