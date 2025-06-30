import {useState} from "react";

const ClusterConfigPage = () => {
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
    <div className="flex flex-col gap-4 max-w-md">
      <p className="text-xl font-medium">Upload kubeconfig</p>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <label className="flex gap-2 items-center">
        <input
          type="checkbox"
          className="w-5 h-5"
          checked={patchLocal}
          onChange={(e) => setPatchLocal(e.target.checked)}
        />
        <span>Patch localhost cluster</span>
      </label>
      <button
        className="bg-blue-500 text-white rounded px-4 py-2 w-fit"
        onClick={upload}
        disabled={!file}
      >
        Upload
      </button>
      {status && <p>{status}</p>}
    </div>
  );
};

export default ClusterConfigPage;