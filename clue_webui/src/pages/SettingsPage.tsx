import {useState, useEffect} from "react";
import {Button, IconButton, Snackbar, Alert} from "@mui/material";
import {styled} from "@mui/material/styles";
import {FileTextIcon, UploadIcon, XIcon} from "@phosphor-icons/react";
import type {ClueConfig} from "../models/ResultsDetails";

const VisuallyHiddenInput = styled("input")({
  clip: "rect(0 0 0 0)",
  clipPath: "inset(50%)",
  height: 1,
  overflow: "hidden",
  position: "absolute",
  bottom: 0,
  left: 0,
  whiteSpace: "nowrap",
  width: 1,
});

const SettingsPage = () => {
  const [file, setFile] = useState<File | null>(null);
  const [patchLocal, setPatchLocal] = useState(true);
  const [status, setStatus] = useState<string | null>(null);
  const [savedConfig, setSavedConfig] = useState<ClueConfig | null>(null);
  const [config, setConfig] = useState<ClueConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({open: false, message: "", severity: "success"});

  const hints: Record<keyof ClueConfig, string> = {
    experiment_timeout:
      "The main timeout to kill the experiment, to avoid hanging experiments",
    prometheus_url: "The URL of the prometheus deployed on the host machine",
    docker_registry_address:
      "The docker image registry address for the CLUE deployer.",
    local_public_ip: "The public IP for the workload generator",
    local_port: "The public port for the workload generator",
    remote_platform_arch: "The platform specification for remote components",
    local_platform_arch: "The platform specification for local components",
    target_utilization: "Autoscaling target utilization percentage",
  };

  useEffect(() => {
    fetch("/api/config/clue")
      .then((r) => r.json())
      .then((d: ClueConfig) => {
        setSavedConfig(d);
        setConfig(d);
      })
      .catch(() => {});
  }, []);

  const upload = async () => {
    if (!file) return;
    const text = await file.text();
    const b64 = btoa(text);
    const res = await fetch("/api/cluster/config", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({kubeconfig: b64, patch_local_cluster: patchLocal}),
    });
    if (res.ok) {
      setStatus("Uploaded kubeconfig");
    } else {
      setStatus("Upload failed");
    }
  };

  const handleChange = (field: keyof ClueConfig, value: string) => {
    if (!config) return;
    setConfig({
      ...config,
      [field]:
        field.includes("timeout") ||
        field.includes("port") ||
        field.includes("utilization")
          ? Number(value)
          : value,
    });
  };

  const saveConfig = async () => {
    if (!config) return;
    setSaving(true);
    const res = await fetch("/api/config/clue", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(config),
    });
    if (res.ok) {
      const data: ClueConfig = await res.json();
      setSavedConfig(data);
      setConfig(data);
      setSnack({
        open: true,
        message: "Configuration saved",
        severity: "success",
      });
    } else {
      setSnack({
        open: true,
        message: "Failed to save configuration",
        severity: "error",
      });
    }
    setSaving(false);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="w-full bg-white rounded-xl shadow-md flex flex-col gap-2 p-6">
        <span className="font-large text-lg font-semibold">
          CLUE Configuration
        </span>
        <span className="text-sm text-gray-500 mb-2">
          Edit the main CLUE configuration used by the deployer.
        </span>
        <div className="w-full flex gap-2">
          <div className="flex w-1/3 flex-col gap-2">
            {config && (
              <>
                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Experiment timeout</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.experiment_timeout}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="number"
                  value={config.experiment_timeout}
                  onChange={(e) =>
                    handleChange("experiment_timeout", e.target.value)
                  }
                />

                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Prometheus URL</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.prometheus_url}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="text"
                  value={config.prometheus_url}
                  onChange={(e) =>
                    handleChange("prometheus_url", e.target.value)
                  }
                />

                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Local public IP</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.local_public_ip}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="text"
                  value={config.local_public_ip}
                  onChange={(e) =>
                    handleChange("local_public_ip", e.target.value)
                  }
                />

                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Local port</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.local_port}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="number"
                  value={config.local_port}
                  onChange={(e) => handleChange("local_port", e.target.value)}
                />
              </>
            )}
          </div>
          <div className="flex w-1/3 flex-col gap-2">
            {config && (
              <>
                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Remote platform arch</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.remote_platform_arch}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="text"
                  value={config.remote_platform_arch}
                  onChange={(e) =>
                    handleChange("remote_platform_arch", e.target.value)
                  }
                />
                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Local platform arch</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.local_platform_arch}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="text"
                  value={config.local_platform_arch}
                  onChange={(e) =>
                    handleChange("local_platform_arch", e.target.value)
                  }
                />

                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Docker registry address</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.docker_registry_address}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="text"
                  value={config.docker_registry_address}
                  onChange={(e) =>
                    handleChange("docker_registry_address", e.target.value)
                  }
                />

                <label className="flex flex-col gap-1 text-sm font-medium">
                  <span>Target utilization</span>
                  <span className="text-xs font-normal text-gray-500">
                    {hints.target_utilization}
                  </span>
                </label>
                <input
                  className="border p-2"
                  type="number"
                  value={config.target_utilization}
                  onChange={(e) =>
                    handleChange("target_utilization", e.target.value)
                  }
                />
              </>
            )}
          </div>
          <div className="w-1/3 flex flex-col bg-gray-50 rounded p-4 overflow-auto">
            <p className="font-medium mb-2">Current Config</p>
            <pre className="text-xs whitespace-pre-wrap break-all">
              {savedConfig && JSON.stringify(savedConfig, null, 2)}
            </pre>
          </div>
        </div>
        <div className="flex  w-full">
          <button
            className={`min-w-[300px] max-w-[300px] mt-2 text-white rounded px-4 py-2 ${
              saving ? "bg-gray-400" : "bg-blue-400 hover:bg-blue-500"
            } text-white rounded px-4 py-2 w-fit transition-colors`}
            disabled={saving}
            onClick={saveConfig}
          >
            {saving ? (
              "Updating config..."
            ) : (
              <div className="flex gap-2 items-center w-full justify-center">
                <UploadIcon />
                Update config
              </div>
            )}
          </button>
        </div>
      </div>
      <div className="w-full gap-2s bg-white rounded-xl shadow-md flex flex-col justify-between p-6">
        <div className="flex flex-col gap-2 pb-4">
          <p className="font-large text-lg font-semibold">
            Cluster Configuration
          </p>
          <p>Upload your kube config to connect to a non default cluster.</p>
        </div>
        <div className="flex flex-col gap-4">
          <Button
            component="label"
            role={undefined}
            variant="contained"
            className="max-w-[300px] !bg-blue-400 !hover:bg-blue-500"
            tabIndex={-1}
            startIcon={<FileTextIcon />}
          >
            Choose config
            <VisuallyHiddenInput
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              multiple
            />
          </Button>
          {file && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span>Selected file: {file.name}</span>
              <IconButton
                size="small"
                onClick={() => setFile(null)}
                aria-label="Remove file"
              >
                <XIcon fontSize="small" color="#663d3d" />
              </IconButton>
            </div>
          )}
          <label className="flex gap-2 items-center">
            <input
              type="checkbox"
              className="w-5 h-5"
              checked={patchLocal}
              onChange={(e) => setPatchLocal(e.target.checked)}
            />
            <span>Patch config to use localhost</span>
          </label>
          <button
            className={`${
              file
                ? "bg-blue-400 hover:bg-blue-500"
                : "bg-gray-300 cursor-not-allowed"
            } text-white rounded px-4 py-2 w-fit transition-colors`}
            onClick={upload}
            disabled={!file}
          >
            Upload file
          </button>
          {status && <p>{status}</p>}
        </div>
      </div>
      <Snackbar
        open={snack.open}
        autoHideDuration={4000}
        onClose={() => setSnack({...snack, open: false})}
      >
        <Alert
          onClose={() => setSnack({...snack, open: false})}
          severity={snack.severity}
          sx={{width: "100%"}}
        >
          {snack.message}
        </Alert>
      </Snackbar>
    </div>
  );
};

export default SettingsPage;
