import {useEffect, useState} from "react";
import LogViewer from "../components/LogViewer";

const workloadOptions = ["shaped", "rampup", "pausing", "fixed"];

const ControlsPage = () => {
  const [suts, setSuts] = useState<string[]>([]);
  const [experiments, setExperiments] = useState<string[]>([]);
  const [selectedSut, setSelectedSut] = useState("");
  const [selectedExperiment, setSelectedExperiment] = useState("");
  const [selectedWorkload, setSelectedWorkload] = useState(workloadOptions[0]);
  const [logs, setLogs] = useState("");
  const [iterations, setIterations] = useState(1);
  const [deployOnly, setDeployOnly] = useState(false);

  useEffect(() => {
    fetch("/api/list/sut")
      .then((r) => r.json())
      .then((d) => setSuts(d.suts ?? []))
      .catch(() => setSuts([]));
    fetch("/api/list/experiments")
      .then((r) => r.json())
      .then((d) => setExperiments(d.experiments ?? []))
      .catch(() => setExperiments([]));
  }, []);

 useEffect(() => {
    let es: EventSource | null = null;
    let isMounted = true;

    const init = async () => {
      try {
        const res = await fetch("/api/logs");
        const data = await res.json();
        if (isMounted) {
          setLogs(data.logs ?? "");
        }
      } catch {
        if (isMounted) setLogs("");
      }
      es = new EventSource("/api/logs/stream");
      es.onmessage = (e) => {
        if (isMounted) {
          setLogs((prev) => prev + e.data);
        }
      };
      es.onerror = () => {
        if (es) es.close();
      };
    };

    init();

    return () => {
      isMounted = false;
      if (es) es.close();
    };
  }, []);

  const deploy = async () => {
    if (!selectedSut || !selectedExperiment) return;
    await fetch("/api/deploy/sut", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({sut_name: selectedSut, experiment_name: selectedExperiment}),
    });
  };

  return (
    <div className="flex gap-8">
      <div className="flex flex-col gap-4 max-w-md">
        <div>
          <label className="block text-sm font-medium mb-1">SUT</label>
        <select
          className="border p-2 w-full"
          value={selectedSut}
          onChange={(e) => setSelectedSut(e.target.value)}
        >
          <option value="" disabled>
            Select SUT
          </option>
          {suts.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Experiment</label>
        <select
          className="border p-2 w-full"
          value={selectedExperiment}
          onChange={(e) => setSelectedExperiment(e.target.value)}
        >
          <option value="" disabled>
            Select Experiment
          </option>
          {experiments.map((exp) => (
            <option key={exp} value={exp}>
              {exp}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Workload Type</label>
        <select
          className="border p-2 w-full"
          value={selectedWorkload}
          onChange={(e) => setSelectedWorkload(e.target.value)}
        >
          {workloadOptions.map((w) => (
            <option key={w} value={w}>
              {w}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Number of Iterations</label>
        <input
          type="number"
          min="1"
          className="border p-2 w-full"
          value={iterations}
          onChange={(e) => setIterations(parseInt(e.target.value) || 1)}
        />
      </div>
      <label className="inline-flex items-center gap-2">
        <input
          type="checkbox"
          className="border"
          checked={deployOnly}
          onChange={(e) => setDeployOnly(e.target.checked)}
        />
        Deploy only
      </label>
      <button
        className="border rounded p-2 bg-green-600 text-white hover:bg-green-700"
        onClick={deploy}
      >
        Deploy
      </button>
      </div>
      <div className="flex-1 border p-2 overflow-y-auto h-96 bg-black text-white whitespace-pre-wrap">
        {logs || "No logs"}
      </div>
    </div>
  );
};

export default ControlsPage;
