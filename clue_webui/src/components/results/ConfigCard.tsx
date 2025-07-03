import {useState} from "react";

const ConfigCard: React.FC<{title: string; data: any}> = ({title, data}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border rounded mb-2 bg-white border rounded-sm p-1">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full text-left p-3 bg-gray-50 hover:bg-gray-100 font-medium flex justify-between items-center"
      >
        {title}
        <span>{isOpen ? "−" : "+"}</span>
      </button>
      {isOpen && (
        <div className="p-3 border-t">
          <pre className="text-sm overflow-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default ConfigCard;
