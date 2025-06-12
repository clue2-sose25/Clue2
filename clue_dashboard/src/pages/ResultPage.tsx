import {Fragment, useEffect, useState} from "react";
import type {Metric} from "../models/Metric";
import {
  ArrowLeftIcon,
  DownloadSimpleIcon,
  RepeatIcon,
} from "@phosphor-icons/react";
import {Link, useParams} from "react-router";
import type {ResultEntry} from "../models/ResultEntry";

// Define params type for useParams
type ResultEntryParams = {
  resultEntryId?: string;
};

const ResultPage = () => {
  // The ID of the results
  const {resultEntryId} = useParams<ResultEntryParams>();
  console.log(resultEntryId);

  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [resultEntry, setResultEntry] = useState<ResultEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    <Fragment>
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
            <button className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
              <RepeatIcon size={20} /> REPEAT BENCHMARK
            </button>
            <button className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
              <DownloadSimpleIcon size={20} /> DOWNLOAD RESULTS
            </button>
          </div>
        </div>

        {/* Header */}
        <div className="mb-8">
          <p className="text-xl font-medium">Experiment:</p>
          <p className="text-lg text-gray-700">
            {resultEntry.id || "No path specified"}
          </p>
        </div>

        {/* Config Info */}
        <div className="bg-gray-100 dark:bg-gray-400 rounded p-4 text-sm leading-relaxed">
          <div>
            <strong>Config:</strong>
          </div>
          <div>SUT: TO-DO</div>
          <div>Experiment: {resultEntry.branch_name}</div>
          <div>Workload type: {resultEntry.workload}</div>
          <div>Iterations: {resultEntry.iterations}</div>
          <div>Timestamp: {resultEntry.timestamp}</div>
        </div>

        {/* Summary Cards */}
        <div className="flex flex-col gap-6 mt-8">
          <h3 className="text-sm font-semibold">Results Summary</h3>
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
    </Fragment>
  );
};

export default ResultPage;
