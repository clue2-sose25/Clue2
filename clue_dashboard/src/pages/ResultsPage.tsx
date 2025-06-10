import { useEffect, useState } from "react";

const ResultsPage = () => {
  interface Metric {
    label: string;
    value: string | number;
}

  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [experimentInfo, setExperimentInfo] = useState<{
    experimentPath: string;
    sut: string;
    experiment: string;
    workload: string;
  } | null>(null);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [metricsRes, infoRes] = await Promise.all([
          fetch("/api/metrics"),
          fetch("/api/experiment-info"),
        ]);

        const metricsData = await metricsRes.json();
        const experimentData = await infoRes.json();

        setMetrics(metricsData);
        setExperimentInfo(experimentData);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading || !experimentInfo) {
    return <div className="p-4">Loading...</div>;
  }

  const { experimentPath, sut, experiment, workload } = experimentInfo;

  //const experimentPath = "2025-05-30_08-31-21\\exp_scale_scale_shaped\\baseline_vanilla_cpu\\0";
  //const sut = "Teastore";
  //const experiment = "Vanilla";
  //const workload = "Shaped";

  return (
    <>
      <div className="flex flex-col gap-4">
        {/* Top Bar mit Back-Link und Buttons */}
        <div className="flex justify-between items-center">
          {/* Back Link links */}
          <a href="#" className="text-sm text-gray-600 hover:underline">
            ← Back
          </a>

        {/* Buttons rechts */}
        <div className="flex gap-4">
          <button className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
            🔁 REPEAT BENCHMARK
          </button>
          <button className="flex items-center gap-2 border px-4 py-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
            ⬇️ DOWNLOAD RESULTS
          </button>
        </div>
      </div>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-sm font-semibold">Analysis of experiment:</h1>
          <h2 className="text-lg text-gray-700">{experimentPath}</h2>
        </div>

        {/* Config Info */}
        <div className="bg-gray-100 dark:bg-gray-400 rounded p-4 text-sm leading-relaxed">
          <div><strong>Config:</strong></div>
          <div>SUT: {sut}</div>
          <div>Experiment: {experiment}</div>
          <div>Workload type: {workload}</div>
        </div>

      {/* Summary Cards */}
      <div className="flex flex-col gap-6 mt-8">
        <h1 className="text-sm font-semibold">Results Summary</h1>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {metrics.map((m) => (
            <div
              key={m.label}
              className="border rounded-xl p-4 shadow bg-white dark:bg-gray-400"
            >
              <div className="text-sm text-gray-500">{m.label}</div>
              <div className="text-xl font-bold mt-1 text-center">{m.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Charts (Image Placeholder) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <img src="/api/static/request-chart.png" alt="Request Chart" className="w-full rounded border" />
          <img src="/api/static/resource-chart.png" alt="Resource Efficiency" className="w-full rounded border" />
          <img src="/api/static/platform-chart.png" alt="Platform Overhead" className="w-full rounded border" />
        </div>
      </div>
    </>
  );
};

export default ResultsPage;
