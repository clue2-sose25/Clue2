import {useState} from "react";
import {Button, IconButton} from "@mui/material";
import {styled} from "@mui/material/styles";
import {FileTextIcon, XIcon} from "@phosphor-icons/react";

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

  return (
    <div className="flex flex-col gap-4">
      <div className="w-full gap-2 bg-white rounded-xl shadow-md hover:shadow-lg transition flex flex-col justify-between p-6">
        <div className="flex flex-col gap-2 pb-4">
          <p className="font-large text-lg font-semibold">CLUE settings</p>
          <p>Change the default behaviour of the CLUE deployer</p>
        </div>
      </div>
      <div className="w-full gap-2s bg-white rounded-xl shadow-md hover:shadow-lg transition flex flex-col justify-between p-6">
        <div className="flex flex-col gap-2 pb-4">
          <p className="font-large text-lg font-semibold">Cluster settings</p>
          <p>Upload your kube config to connect to a non default cluster.</p>
        </div>
        <div className="flex flex-col gap-4">
          <Button
            component="label"
            role={undefined}
            variant="contained"
            className="max-w-[300px]"
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
    </div>
  );
};

export default SettingsPage;
