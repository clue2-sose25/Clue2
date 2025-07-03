import React, {useState, useEffect} from "react";
import {
  XIcon,
  PlusIcon,
  ChartBarIcon,
  TrendUpIcon,
} from "@phosphor-icons/react";
import type {Variant, Workload} from "../../models/ResultsDetails";
import type {Metric} from "../../models/Metric";
import type {Plot} from "../../models/Plot";
import type {ComparisonPanel} from "../../models/ComparisonPanel";

// Fallback mocks
const mockMetrics: Metric[] = [
  {name: "Response Time", value: 125.5, unit: "ms"},
  {name: "Throughput", value: 1250, unit: "req/s"},
  {name: "Error Rate", value: 0.05, unit: "%"},
  {name: "CPU Usage", value: 65.2, unit: "%"},
  {name: "Memory Usage", value: 78.9, unit: "%"},
];
const mockPlots: Plot[] = [
  {
    id: "response-time",
    name: "Response Time Over Time",
    description: "Shows response time trends during the test",
    image_url: "/default_plot.png",
  },
  {
    id: "throughput",
    name: "Throughput Analysis",
    description: "Requests per second over time",
    image_url: "/default_plot.png",
  },
  {
    id: "resource-usage",
    name: "Resource Utilization",
    description: "CPU and memory usage during test",
    image_url: "/default_plot.png",
  },
];

const ResultsSection: React.FC<{
  workloads: Workload[];
  variants: Variant[];
  experimentId?: string;
}> = ({workloads, variants, experimentId = "test-uuid"}) => {
  const [comparisonPanels, setComparisonPanels] = useState<ComparisonPanel[]>(
    []
  );
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [selectedWorkload, setSelectedWorkload] = useState<Workload | null>(
    null
  );
  const [selectedVariant, setSelectedVariant] = useState<Variant | null>(null);
  const [selectedIteration, setSelectedIteration] = useState(0);
  const [panelMetrics, setPanelMetrics] = useState<Record<string, Metric[]>>(
    {}
  );
  const [panelPlots, setPanelPlots] = useState<Record<string, Plot[]>>({});

  // Default single panel
  useEffect(() => {
    if (workloads.length && variants.length) {
      const w = workloads[0];
      const v = variants[0];
      const id = `${w.name}-${v.name}-0`;
      setComparisonPanels([{id, workload: w, variant: v, iteration: 0}]);
    }
  }, [workloads, variants]);

  // Fetch with fallback
  const fetchMetrics = async (wl: string, vr: string, it: number) => {
    try {
      const res = await fetch(
        `/api/results/${experimentId}/metrics?workload=${wl}&variant=${vr}&iteration=${it}`
      );
      if (!res.ok) throw new Error();
      return (await res.json()) as Metric[];
    } catch {
      return mockMetrics;
    }
  };
  const fetchPlots = async (wl: string, vr: string, it: number) => {
    try {
      const res = await fetch(
        `/api/results/${experimentId}/plots?workload=${wl}&variant=${vr}&iteration=${it}`
      );
      if (!res.ok) throw new Error();
      return (await res.json()) as Plot[];
    } catch {
      return mockPlots;
    }
  };

  // Load data when panels change
  useEffect(() => {
    comparisonPanels.forEach(async (panel) => {
      const metrics = await fetchMetrics(
        panel.workload.name,
        panel.variant.name,
        panel.iteration
      );
      const plots = await fetchPlots(
        panel.workload.name,
        panel.variant.name,
        panel.iteration
      );
      setPanelMetrics((prev) => ({...prev, [panel.id]: metrics}));
      setPanelPlots((prev) => ({...prev, [panel.id]: plots}));
    });
  }, [comparisonPanels, experimentId]);

  // Add panel
  const addPanel = () => {
    if (!selectedWorkload || !selectedVariant) return;
    const id = `${selectedWorkload.name}-${selectedVariant.name}-${selectedIteration}`;
    if (!comparisonPanels.find((p) => p.id === id)) {
      setComparisonPanels((prev) => [
        ...prev,
        {
          id,
          workload: selectedWorkload,
          variant: selectedVariant,
          iteration: selectedIteration,
        },
      ]);
    }
    setShowAddPanel(false);
    setSelectedWorkload(null);
    setSelectedVariant(null);
    setSelectedIteration(0);
  };

  // Remove panel
  const removePanel = (id: string) => {
    setComparisonPanels((prev) => prev.filter((p) => p.id !== id));
    setPanelMetrics((prev) => {
      const c = {...prev};
      delete c[id];
      return c;
    });
    setPanelPlots((prev) => {
      const c = {...prev};
      delete c[id];
      return c;
    });
  };

  const gridCols =
    comparisonPanels.length === 1
      ? "grid-cols-1"
      : comparisonPanels.length === 2
      ? "grid-cols-2"
      : "grid-cols-3";

  return (
    <div className="mb-8">
      {/* Header */}
      <div className="flex items-center justify-between pb-4">
        <h2 className="text-lg font-medium">Experiment Results</h2>
        <button
          onClick={() => setShowAddPanel(true)}
          className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          <PlusIcon className="w-4 h-4" /> New Panel
        </button>
      </div>

      {/* Add Panel Modal */}
      {showAddPanel && (
        <div className="fixed inset-0 bg-transparent flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-medium mb-4">Add Comparison Panel</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Workload
                </label>
                <select
                  value={selectedWorkload?.name || ""}
                  onChange={(e) =>
                    setSelectedWorkload(
                      workloads.find((w) => w.name === e.target.value) || null
                    )
                  }
                  className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select a workload</option>
                  {workloads.map((w) => (
                    <option key={w.name} value={w.name}>
                      {w.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Variant
                </label>
                <select
                  value={selectedVariant?.name || ""}
                  onChange={(e) =>
                    setSelectedVariant(
                      variants.find((v) => v.name === e.target.value) || null
                    )
                  }
                  className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select a variant</option>
                  {variants.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Iteration
                </label>
                <select
                  value={selectedIteration}
                  onChange={(e) =>
                    setSelectedIteration(parseInt(e.target.value))
                  }
                  className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                >
                  {[0, 1, 2, 3, 4, 5].map((i) => (
                    <option key={i} value={i}>
                      Iteration {i}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end space-x-2 mt-6">
              <button
                onClick={() => setShowAddPanel(false)}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={addPanel}
                disabled={!selectedWorkload || !selectedVariant}
                className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Panels Grid */}
      <div className={`grid ${gridCols} gap-4`}>
        {comparisonPanels.map((panel) => (
          <div
            key={panel.id}
            className="bg-white border rounded-lg overflow-hidden"
          >
            {/* Header with inline dropdowns */}
            <div className="bg-gray-50 p-3 border-b flex justify-between items-center">
              <div className="flex items-center gap-1">
                <select
                  value={panel.workload.name}
                  onChange={(e) => {
                    const w = workloads.find((w) => w.name === e.target.value)!;
                    const updated = {
                      ...panel,
                      workload: w,
                      id: `${w.name}-${panel.variant.name}-${panel.iteration}`,
                    };
                    setComparisonPanels((prev) =>
                      prev.map((p) => (p.id === panel.id ? updated : p))
                    );
                  }}
                  className="text-sm font-medium"
                >
                  {workloads.map((w) => (
                    <option key={w.name} value={w.name}>
                      {w.name}
                    </option>
                  ))}
                </select>
                <span className="text-gray-400">/</span>
                <select
                  value={panel.variant.name}
                  onChange={(e) => {
                    const v = variants.find((v) => v.name === e.target.value)!;
                    const updated = {
                      ...panel,
                      variant: v,
                      id: `${panel.workload.name}-${v.name}-${panel.iteration}`,
                    };
                    setComparisonPanels((prev) =>
                      prev.map((p) => (p.id === panel.id ? updated : p))
                    );
                  }}
                  className="text-sm font-medium"
                >
                  {variants.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.name}
                    </option>
                  ))}
                </select>
                <span className="text-gray-400">/</span>
                <select
                  value={panel.iteration}
                  onChange={(e) => {
                    const it = parseInt(e.target.value);
                    const updated = {
                      ...panel,
                      iteration: it,
                      id: `${panel.workload.name}-${panel.variant.name}-${it}`,
                    };
                    setComparisonPanels((prev) =>
                      prev.map((p) => (p.id === panel.id ? updated : p))
                    );
                  }}
                  className="text-sm font-medium"
                >
                  {[0, 1, 2, 3, 4, 5].map((i) => (
                    <option key={i} value={i}>
                      Iteration {i}
                    </option>
                  ))}
                </select>
              </div>
              <button onClick={() => removePanel(panel.id)}>
                <XIcon className="w-4 h-4 text-gray-400 hover:text-red-500" />
              </button>
            </div>
            {/* Content */}
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="font-medium mb-1">Workload Details</div>
                  <p className="text-gray-600 mb-2">
                    {panel.workload.description}
                  </p>
                  <div className="text-gray-500">
                    Timeout: {panel.workload.timeout_duration}s
                  </div>
                </div>
                <div>
                  <div className="font-medium mb-1">Variant Details</div>
                  <p className="text-gray-600 mb-2">
                    {panel.variant.description}
                  </p>
                  <div className="space-y-1 text-gray-500">
                    <div>Branch: {panel.variant.target_branch}</div>
                    <div>Autoscaling: {panel.variant.autoscaling}</div>
                    <div>Max Scale: {panel.variant.max_autoscale}</div>
                    <div>
                      Colocated:{" "}
                      {panel.variant.colocated_workload ? "Yes" : "No"}
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1 mb-2">
                  <TrendUpIcon className="w-4 h-4" />
                  <span className="font-medium text-sm">Metrics</span>
                </div>
                <div className="space-y-1 text-xs">
                  {(panelMetrics[panel.id] || []).map((m, i) => (
                    <div key={i} className="flex justify-between">
                      <span className="text-gray-600">{m.name}</span>
                      <span className="font-medium">
                        {m.value} {m.unit}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1 mb-2">
                  <ChartBarIcon className="w-4 h-4" />
                  <span className="font-medium text-sm">Plots</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(panelPlots[panel.id] || []).map((p) => (
                    <div
                      key={p.id}
                      className="border rounded p-2 text-xs flex-1 min-w-[335px] max-w-[250px]"
                    >
                      <div className="font-medium mb-1">{p.name}</div>
                      <div className="mb-2 text-gray-600">{p.description}</div>
                      <img
                        src={p.image_url}
                        alt={p.name}
                        className="w-full h-auto max-h-128 object-cover rounded"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultsSection;
