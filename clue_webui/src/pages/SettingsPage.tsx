import {useState} from "react";

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
      <div className="w-full gap-2 bg-white rounded-xl shadow-md flex flex-col justify-between p-6">
        <div className="flex flex-col gap-2 pb-4">
          <p className="font-large text-lg font-semibold">CLUE settings</p>
          <p>Change the default behaviour of the CLUE deployer</p>
        </div>
      </div>
      <div className="w-full gap-2s bg-white rounded-xl shadow-md flex flex-col justify-between p-6">
        <div className="flex flex-col gap-2 pb-4">
          <p className="font-large text-lg font-semibold">Cluster settings</p>
          <p>Upload your .kube config to connect to a non default cluster.</p>
        </div>
        <div className="flex flex-col gap-4">
          <input
            type="file"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition-colors cursor-pointer"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
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
            className="bg-blue-500 text-white rounded px-4 py-2 w-fit"
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
