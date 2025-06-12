import {TrashIcon} from "@phosphor-icons/react";
import {useEffect, useState} from "react";
import {Link} from "react-router";

interface Iteration {
  workload: string;
  branch_name: string;
  experiment_number: number;
}

interface ResultEntry {
  timestamp: string;
  iterations: Iteration[];
}

const ExperimentsResultsPage = () => {
  const [results, setResults] = useState<ResultEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/api/list/results")
      .then((res) => {
        if (!res.ok) throw new Error("Request failed");
        return res.json();
      })
      .then((data) => {
        setResults(data.results);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-6">Loading results...</div>;

  if (error || !results || results.length === 0) {
    return (
      <div className="flex justify-center items-center h-[50vh] text-xl text-gray-500 text-center">
        No experiments found. <br /> Deploy an experiment to see its results.
      </div>
    );
  }

  return (
    <div className="p-6">
      <h3 className="text-2xl font-semibold mb-4">Experiment Results</h3>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300 rounded-lg shadow-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="text-left px-4 py-3 border-b border-gray-300 font-semibold text-gray-700">
                Timestamp
              </th>
              <th className="text-left px-4 py-3 border-b border-gray-300 font-semibold text-gray-700">
                Workload
              </th>
              <th className="text-left px-4 py-3 border-b border-gray-300 font-semibold text-gray-700">
                Branch
              </th>
              <th className="text-left px-4 py-3 border-b border-gray-300 font-semibold text-gray-700">
                Experiment #
              </th>
              <th className="text-left px-4 py-3 border-b border-gray-300 font-semibold text-gray-700 w-20">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white">
            {results.map((result, i) =>
              result.iterations.map((iter, j) => (
                <tr
                  key={`${i}-${j}`}
                  className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 text-gray-900">
                    <Link
                      to={`/results/${iter.branch_name}`}
                      className="block w-full h-full hover:text-blue-600 transition-colors"
                    >
                      {result.timestamp}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    <Link
                      to={`/results/${iter.branch_name}`}
                      className="block w-full h-full hover:text-blue-600 transition-colors"
                    >
                      {iter.workload}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    <Link
                      to={`/results/${iter.branch_name}`}
                      className="block w-full h-full hover:text-blue-600 transition-colors"
                    >
                      {iter.branch_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    <Link
                      to={`/results/${iter.branch_name}`}
                      className="block w-full h-full hover:text-blue-600 transition-colors"
                    >
                      {iter.experiment_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="p-1 rounded hover:bg-red-100 text-red-600 hover:text-red-700 transition-colors"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        // Handle delete action here
                        console.log("Delete clicked for:", iter.branch_name);
                      }}
                      aria-label="Delete experiment"
                    >
                      <TrashIcon size={18} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ExperimentsResultsPage;
