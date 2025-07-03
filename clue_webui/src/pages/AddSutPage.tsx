import {useEffect, useState} from "react";
import {Link, useNavigate} from "react-router";
import {ArrowLeftIcon, UploadSimpleIcon} from "@phosphor-icons/react";

const AddSutPage = () => {
  const [file, setFile] = useState<File | null>(null);
  const [content, setContent] = useState<string>("");
  const [sutName, setSutName] = useState<string>("");
  const navigate = useNavigate();

  const parseSutName = (yaml: string) => {
    const match = yaml.match(/^\s*sut:\s*"?([A-Za-z0-9-_]+)"?/m);
    if (match) {
      setSutName(match[1]);
    }
  };

  useEffect(() => {
    fetch("/api/suts/raw/default_sut")
      .then((r) => r.text())
      .then((t) => {
        setContent(t);
        parseSutName(t);
      })
      .catch(() => {});
  }, []);

  const loadFile = async (f: File) => {
    const text = await f.text();
    setContent(text);
    setFile(f);
    parseSutName(text);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      void loadFile(f);
    }
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) {
      void loadFile(f);
    }
  };

  const addSut = async () => {
    let yaml = content;
    if (sutName) {
      if (yaml.match(/^\s*sut:/m)) {
        yaml = yaml.replace(/^\s*sut:\s*.*$/m, `  sut: "${sutName}"`);
      }
    }
    const encoded = btoa(yaml);
    const res = await fetch("/api/suts", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({sut_config: encoded}),
    });
    if (res.ok) {
      navigate("/experiment");
    }
  };

  return (
    <div className="w-full h-full flex flex-col gap-4 p-4 overflow-y-auto">
      <Link
        to="/experiment"
        className="flex gap-2 items-center text-sm text-gray-600 hover:underline"
      >
        <ArrowLeftIcon /> Back
      </Link>
      <div
        className="border-2 border-dashed rounded p-6 flex flex-col items-center justify-center text-center gap-2"
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
      >
        <p className="text-sm">Drag and drop a SUT config file here</p>
        <label className="bg-blue-500 text-white px-4 py-2 rounded cursor-pointer" >
          Choose File
          <input type="file" className="hidden" onChange={onFileChange} />
        </label>
        {file && <p className="text-xs text-gray-600">{file.name}</p>}
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium" htmlFor="sut-name-input">
          SUT Name
        </label>
        <input
          id="sut-name-input"
          className="border p-2"
          type="text"
          value={sutName}
          onChange={(e) => setSutName(e.target.value)}
        />
      </div>
      <textarea
        className="border p-2 font-mono text-sm w-full h-64"
        value={content}
        onChange={(e) => setContent(e.target.value)}
      ></textarea>
      <div className="flex w-full justify-center">
        <button
          type="button"
          className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white rounded shadow px-4 py-2"
          onClick={addSut}
        >
          <UploadSimpleIcon size={16} /> Add SUT
        </button>
      </div>
    </div>
  );
};

export default AddSutPage;