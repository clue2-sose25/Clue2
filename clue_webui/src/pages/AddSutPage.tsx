import {useEffect, useState, useRef} from "react";
import {Link, useNavigate} from "react-router";
import {ArrowLeftIcon, UploadSimpleIcon} from "@phosphor-icons/react";

const AddSutPage = () => {
  const [file, setFile] = useState<File | null>(null);
  const [content, setContent] = useState<string>("");
  const [sutName, setSutName] = useState<string>("");
  const [displayName, setDisplayName] = useState<string>("");
  const navigate = useNavigate();

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const parseSutName = (yaml: string) => {
    const match = yaml.match(/^\s*sut:\s*"?([A-Za-z0-9-_]+)"?/m);
    if (match) {
      const name = match[1];
      setSutName(name);
      setDisplayName(name.endsWith(".yaml") ? name : `${name}.yaml`);
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

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setDisplayName(value);
    setSutName(value.replace(/\.yaml$/, ""));
  };

  const addSut = async () => {
    let yaml = content;
    const finalName = sutName || displayName.replace(/\.yaml$/, "");
    if (finalName) {
      if (yaml.match(/^\s*sut:/m)) {
        yaml = yaml.replace(/^\s*sut:\s*.*$/m, `  sut: "${finalName}"`);
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
    <div className="w-full h-full flex flex-col gap-3 p-4 overflow-y-auto">
      <Link
        to="/experiment"
        className="flex gap-2 items-center text-sm text-gray-600 hover:underline"
      >
        <ArrowLeftIcon /> Back
      </Link>

      <div className="flex gap-6 flex-1 min-h-0">
        {/* Left Column - Controls */}
        <div className="flex flex-col gap-3 w-1/3 pr-4">
          <label className="text-sm font-medium" htmlFor="sut-name-input">
            Create new SUT config
          </label>
          <p className="text-xs text-gray-600">
            If you have an existing config file, you can select it below to
            edit. Note that loading a file will replace the current content in
            the text area.
          </p>

          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-4 flex flex-col items-center justify-center text-center gap-2 hover:border-gray-400 transition-colors"
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
          >
            <p className="text-sm text-gray-600">
              Drag and drop existing SUT config
            </p>
            <label className="bg-blue-500 text-white px-3 py-1.5 rounded cursor-pointer text-sm hover:bg-blue-600 transition-colors">
              Choose File
              <input
                type="file"
                className="hidden"
                onChange={onFileChange}
                accept=".yaml,.yml"
              />
            </label>
            {file && <p className="text-xs text-gray-500">{file.name}</p>}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium" htmlFor="sut-name-input">
              File name
            </label>
            <input
              id="sut-name-input"
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              type="text"
              value={displayName}
              onChange={handleNameChange}
              placeholder="Enter SUT name"
              onBlur={(e) => {
                const value = e.target.value;
                if (value && !value.endsWith(".yaml")) {
                  setDisplayName(value + ".yaml");
                }
              }}
            />
          </div>

          <div className="flex w-full justify-center pt-2">
            <button
              type="button"
              className="flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg shadow px-4 py-2 transition-colors"
              onClick={addSut}
            >
              <UploadSimpleIcon size={16} /> Upload the SUT config
            </button>
          </div>
        </div>

        {/* Right Column - YAML Editor */}
        <div className="flex-1 flex flex-col gap-2 min-h-0">
          <label className="text-sm font-medium">Configuration (YAML)</label>
          <div className="flex-1 relative border border-gray-300 rounded-lg overflow-hidden bg-white">
            <textarea
              ref={textareaRef}
              className="absolute inset-0 w-full h-full p-3 font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset bg-white text-black"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Enter your YAML configuration here..."
              spellCheck={false}
              wrap="off"
              style={{
                fontFamily:
                  'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                lineHeight: "1.5",
                tabSize: 2,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default AddSutPage;
