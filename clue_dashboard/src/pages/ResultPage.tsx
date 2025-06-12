import {useEffect, useState} from "react";
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
  const [error, setError] = useState<string | null>(null);

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
      setError(null);

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
      } catch (err) {
        console.error("Error fetching data:", err);
        setError(
          err instanceof Error ? err.message : "An unexpected error occurred"
        );
        setMetrics([]);
        setResultEntry(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [resultEntryId]);

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  if (error || !resultEntry) {
    return <div className="p-4">Error: {error || "No data available"}</div>;
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {metrics.length > 0 ? (
              metrics.map((m) => (
                <div
                  key={m.label}
                  className="border rounded-xl p-4 shadow bg-white dark:bg-gray-400"
                >
                  <div className="text-sm text-gray-500">{m.label}</div>
                  <div className="text-xl font-bold mt-1 text-center">
                    {m.value}
                  </div>
                </div>
              ))
            ) : (
              <div>No metrics available</div>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <img
              src="/api/static/request-chart.png"
              alt="Request Chart"
              className="w-full rounded border"
            />
            <img
              src="/api/static/resource-chart.png"
              alt="Resource Efficiency"
              className="w-full rounded border"
            />
            <img
              src="/api/static/platform-chart.png"
              alt="Platform Overhead"
              className="w-full rounded border"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultPage;
