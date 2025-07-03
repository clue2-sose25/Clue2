import {useState, useEffect} from "react";
import {
  XIcon,
  PlusIcon,
  ChartBarIcon,
  TrendUpIcon,
} from "@phosphor-icons/react";

// Types based on your models
interface WorkloadSettings {
  [key: string]: any;
}

interface Workload {
  name: string;
  description: string;
  timeout_duration: number;
  workload_settings: WorkloadSettings;
}

interface Variant {
  name: string;
  target_branch: string;
  critical_services: string[];
  colocated_workload: boolean;
  autoscaling: string;
  max_autoscale: number;
  description: string;
}

interface ComparisonPanel {
  id: string;
  workload: Workload;
  variant: Variant;
  iteration: number;
}

interface Metric {
  name: string;
  value: number;
  unit: string;
  description?: string;
}

interface Plot {
  id: string;
  name: string;
  description: string;
  image_url: string;
}

// Mock data for demonstration
const mockWorkloads: Workload[] = [
  {
    name: "Load Test",
    description: "High-volume load testing scenario",
    timeout_duration: 300,
    workload_settings: {
      concurrent_users: 100,
      ramp_up_time: 30,
      test_duration: 300,
    },
  },
  {
    name: "Stress Test",
    description: "System stress testing with peak loads",
    timeout_duration: 600,
    workload_settings: {
      concurrent_users: 500,
      ramp_up_time: 60,
      test_duration: 600,
    },
  },
];

const mockVariants: Variant[] = [
  {
    name: "Baseline",
    target_branch: "main",
    critical_services: ["api", "database"],
    colocated_workload: false,
    autoscaling: "horizontal",
    max_autoscale: 10,
    description: "Baseline configuration",
  },
  {
    name: "Optimized",
    target_branch: "feature/optimization",
    critical_services: ["api", "database", "cache"],
    colocated_workload: true,
    autoscaling: "vertical",
    max_autoscale: 20,
    description: "Optimized configuration with caching",
  },
  {
    name: "Experimental",
    target_branch: "feature/experimental",
    critical_services: ["api", "database", "cache", "monitoring"],
    colocated_workload: true,
    autoscaling: "both",
    max_autoscale: 15,
    description: "Experimental features enabled",
  },
];

const mockMetrics: Metric[] = [
  {
    name: "Response Time",
    value: 125.5,
    unit: "ms",
    description: "Average response time",
  },
  {
    name: "Throughput",
    value: 1250,
    unit: "req/s",
    description: "Requests per second",
  },
  {
    name: "Error Rate",
    value: 0.05,
    unit: "%",
    description: "Percentage of failed requests",
  },
  {
    name: "CPU Usage",
    value: 65.2,
    unit: "%",
    description: "Average CPU utilization",
  },
  {
    name: "Memory Usage",
    value: 78.9,
    unit: "%",
    description: "Average memory utilization",
  },
];

const mockPlots: Plot[] = [
  {
    id: "response-time",
    name: "Response Time Over Time",
    description: "Shows response time trends during the test",
    image_url:
      "https://via.placeholder.com/400x300/f0f0f0/666666?text=Response+Time+Chart",
  },
  {
    id: "throughput",
    name: "Throughput Analysis",
    description: "Requests per second over time",
    image_url:
      "https://via.placeholder.com/400x300/f0f0f0/666666?text=Throughput+Chart",
  },
  {
    id: "resource-usage",
    name: "Resource Utilization",
    description: "CPU and memory usage during test",
    image_url:
      "https://via.placeholder.com/400x300/f0f0f0/666666?text=Resource+Usage+Chart",
  },
];

const ResultsSection: React.FC<{
  workloads: Workload[];
  variants: Variant[];
  experimentId?: string;
}> = ({
  workloads = mockWorkloads,
  variants = mockVariants,
  experimentId = "test-uuid",
}) => {
  const [comparisonPanels, setComparisonPanels] = useState<ComparisonPanel[]>(
    []
  );
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [selectedWorkload, setSelectedWorkload] = useState<Workload | null>(
    null
  );
  const [selectedVariant, setSelectedVariant] = useState<Variant | null>(null);
  const [selectedIteration, setSelectedIteration] = useState(1);
  const [panelMetrics, setPanelMetrics] = useState<{[key: string]: Metric[]}>(
    {}
  );
  const [panelPlots, setPanelPlots] = useState<{[key: string]: Plot[]}>({});
  const [editingPanel, setEditingPanel] = useState<{
    panelId: string;
    field: "workload" | "variant" | "iteration";
  } | null>(null);

  // Initialize with first workload and up to 3 variants
  useEffect(() => {
    if (workloads.length > 0 && variants.length > 0) {
      const firstWorkload = workloads[0];
      const initialPanels = variants.slice(0, 3).map((variant, index) => ({
        id: `${firstWorkload.name}-${variant.name}-1`,
        workload: firstWorkload,
        variant: variant,
        iteration: 1,
      }));
      setComparisonPanels(initialPanels);
    }
  }, [workloads, variants]);

  // Mock API calls - replace with actual API calls
  const fetchMetrics = async (
    workload: string,
    variant: string,
    iteration: number
  ) => {
    // In real implementation:
    // const response = await fetch(`/api/results/${experimentId}/metrics?workload=${workload}&variant=${variant}&iteration=${iteration}`);
    // return response.json();
    return mockMetrics;
  };

  const fetchPlots = async (
    workload: string,
    variant: string,
    iteration: number
  ) => {
    // In real implementation:
    // const response = await fetch(`/api/results/${experimentId}/plot?workload=${workload}&variant=${variant}&iteration=${iteration}`);
    // return response.json();
    return mockPlots;
  };

  // Load data for panels
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

  const addPanel = () => {
    if (selectedWorkload && selectedVariant) {
      const newPanel: ComparisonPanel = {
        id: `${selectedWorkload.name}-${selectedVariant.name}-${selectedIteration}`,
        workload: selectedWorkload,
        variant: selectedVariant,
        iteration: selectedIteration,
      };

      // Check if this combination already exists
      const exists = comparisonPanels.some((panel) => panel.id === newPanel.id);
      if (!exists) {
        setComparisonPanels([...comparisonPanels, newPanel]);
      }

      setShowAddPanel(false);
      setSelectedWorkload(null);
      setSelectedVariant(null);
      setSelectedIteration(1);
    }
  };

  const updatePanel = (
    panelId: string,
    field: "workload" | "variant" | "iteration",
    value: any
  ) => {
    setComparisonPanels((prev) =>
      prev.map((panel) => {
        if (panel.id === panelId) {
          const updatedPanel = {...panel};
          if (field === "workload") {
            updatedPanel.workload = value;
          } else if (field === "variant") {
            updatedPanel.variant = value;
          } else if (field === "iteration") {
            updatedPanel.iteration = value;
          }
          updatedPanel.id = `${updatedPanel.workload.name}-${updatedPanel.variant.name}-${updatedPanel.iteration}`;
          return updatedPanel;
        }
        return panel;
      })
    );
    setEditingPanel(null);
  };
  const removePanel = (panelId: string) => {
    setComparisonPanels(
      comparisonPanels.filter((panel) => panel.id !== panelId)
    );
    setPanelMetrics((prev) => {
      const newMetrics = {...prev};
      delete newMetrics[panelId];
      return newMetrics;
    });
    setPanelPlots((prev) => {
      const newPlots = {...prev};
      delete newPlots[panelId];
      return newPlots;
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
      <div className="flex flex-col gap-1 pb-4">
        <div className="flex items-center justify-between">
          <div className="text-lg font-medium">Experiment Results</div>
          <button
            onClick={() => setShowAddPanel(true)}
            className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            <PlusIcon className="w-4 h-4" />
            Add Panel
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Compare different workload/variant/iteration combinations. Add new
          panels or close existing ones to customize your view.
        </p>
      </div>

      {/* Add Panel Modal */}
      {showAddPanel && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50">
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
                  {workloads.map((workload) => (
                    <option key={workload.name} value={workload.name}>
                      {workload.name}
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
                  {variants.map((variant) => (
                    <option key={variant.name} value={variant.name}>
                      {variant.name}
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
                  {[1, 2, 3, 4, 5].map((i) => (
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
                Add Panel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Panel Modal */}
      {editingPanel && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <h3 className="text-lg font-medium mb-4">
              Edit{" "}
              {editingPanel.field === "workload"
                ? "Workload"
                : editingPanel.field === "variant"
                ? "Variant"
                : "Iteration"}
            </h3>

            <div className="space-y-4">
              {editingPanel.field === "workload" && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Workload
                  </label>
                  <select
                    defaultValue={
                      comparisonPanels.find(
                        (p) => p.id === editingPanel.panelId
                      )?.workload.name
                    }
                    onChange={(e) => {
                      const workload = workloads.find(
                        (w) => w.name === e.target.value
                      );
                      if (workload)
                        updatePanel(editingPanel.panelId, "workload", workload);
                    }}
                    className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                  >
                    {workloads.map((workload) => (
                      <option key={workload.name} value={workload.name}>
                        {workload.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {editingPanel.field === "variant" && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Variant
                  </label>
                  <select
                    defaultValue={
                      comparisonPanels.find(
                        (p) => p.id === editingPanel.panelId
                      )?.variant.name
                    }
                    onChange={(e) => {
                      const variant = variants.find(
                        (v) => v.name === e.target.value
                      );
                      if (variant)
                        updatePanel(editingPanel.panelId, "variant", variant);
                    }}
                    className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                  >
                    {variants.map((variant) => (
                      <option key={variant.name} value={variant.name}>
                        {variant.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {editingPanel.field === "iteration" && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Iteration
                  </label>
                  <select
                    defaultValue={
                      comparisonPanels.find(
                        (p) => p.id === editingPanel.panelId
                      )?.iteration
                    }
                    onChange={(e) => {
                      updatePanel(
                        editingPanel.panelId,
                        "iteration",
                        parseInt(e.target.value)
                      );
                    }}
                    className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                  >
                    {[1, 2, 3, 4, 5].map((i) => (
                      <option key={i} value={i}>
                        Iteration {i}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-2 mt-6">
              <button
                onClick={() => setEditingPanel(null)}
                className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Comparison Panels */}
      {comparisonPanels.length > 0 && (
        <div className={`grid ${gridCols} gap-4`}>
          {comparisonPanels.map((panel) => (
            <div
              key={panel.id}
              className="bg-white border rounded-lg overflow-hidden"
            >
              {/* Panel Header */}
              <div className="bg-gray-50 p-3 border-b">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() =>
                        setEditingPanel({panelId: panel.id, field: "workload"})
                      }
                      className="text-sm font-medium text-blue-600 hover:text-blue-800 underline"
                    >
                      {panel.workload.name}
                    </button>
                    <span className="text-sm text-gray-400">/</span>
                    <button
                      onClick={() =>
                        setEditingPanel({panelId: panel.id, field: "variant"})
                      }
                      className="text-sm font-medium text-blue-600 hover:text-blue-800 underline"
                    >
                      {panel.variant.name}
                    </button>
                    <span className="text-sm text-gray-400">/</span>
                    <button
                      onClick={() =>
                        setEditingPanel({panelId: panel.id, field: "iteration"})
                      }
                      className="text-sm font-medium text-blue-600 hover:text-blue-800 underline"
                    >
                      Iteration {panel.iteration}
                    </button>
                  </div>
                  <button
                    onClick={() => removePanel(panel.id)}
                    className="text-gray-400 hover:text-red-500"
                  >
                    <XIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Panel Content */}
              <div className="p-4 space-y-4">
                {/* Workload and Variant Info Side by Side */}
                <div className="grid grid-cols-2 gap-4 text-xs">
                  {/* Workload Info */}
                  <div>
                    <div className="font-medium mb-1">Workload Details</div>
                    <p className="text-gray-600 mb-2">
                      {panel.workload.description}
                    </p>
                    <div className="text-gray-500">
                      Timeout: {panel.workload.timeout_duration}s
                    </div>
                  </div>

                  {/* Variant Info */}
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

                {/* Metrics */}
                <div>
                  <div className="flex items-center gap-1 mb-2">
                    <TrendUpIcon className="w-4 h-4" />
                    <span className="font-medium text-sm">Metrics</span>
                  </div>
                  <div className="space-y-1">
                    {(panelMetrics[panel.id] || []).map((metric, idx) => (
                      <div
                        key={idx}
                        className="flex justify-between items-center text-xs"
                      >
                        <span className="text-gray-600">{metric.name}</span>
                        <span className="font-medium">
                          {metric.value} {metric.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Plots */}
                <div>
                  <div className="flex items-center gap-1 mb-2">
                    <ChartBarIcon className="w-4 h-4" />
                    <span className="font-medium text-sm">Plots</span>
                  </div>
                  <div className="space-y-2">
                    {(panelPlots[panel.id] || []).map((plot) => (
                      <div key={plot.id} className="border rounded p-2">
                        <div className="text-xs font-medium mb-1">
                          {plot.name}
                        </div>
                        <div className="text-xs text-gray-600 mb-2">
                          {plot.description}
                        </div>
                        <img
                          src={plot.image_url}
                          alt={plot.name}
                          className="w-full h-32 object-cover rounded"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {comparisonPanels.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No comparison panels added yet.</p>
          <p className="text-sm">
            Click "Add Panel" to start comparing results.
          </p>
        </div>
      )}
    </div>
  );
};

export default ResultsSection;
