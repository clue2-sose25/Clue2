import {useEffect, useState} from "react";

interface Iteration {
  workload: string;
  branch_name: string;
  experiment_number: number;
}

interface ResultEntry {
  timestamp: string;
  iterations: Iteration[];
}

const ExperimentsPage = () => {
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
        if (!data.results || data.results.length === 0) {
          setError(true);
        } else {
          setResults(data.results);
        }
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-6">Loading...</div>;

  if (error) {
    return (
      <div className="flex justify-center items-center h-[50vh] text-xl text-gray-500">
        No experiments found
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Experiment Results</h1>

      <table className="min-w-full border border-gray-300 rounded shadow">
        <thead className="bg-gray-100">
          <tr>
            <th className="text-left px-4 py-2 border-b">Timestamp</th>
            <th className="text-left px-4 py-2 border-b">Workload</th>
            <th className="text-left px-4 py-2 border-b">Branch</th>
            <th className="text-left px-4 py-2 border-b">Experiment #</th>
          </tr>
        </thead>
        <tbody>
          {results.map((result, i) =>
            result.iterations.map((iter, j) => (
              <tr key={`${i}-${j}`} className="hover:bg-gray-50">
                <td className="px-4 py-2 border-b">{result.timestamp}</td>
                <td className="px-4 py-2 border-b">{iter.workload}</td>
                <td className="px-4 py-2 border-b">{iter.branch_name}</td>
                <td className="px-4 py-2 border-b">{iter.experiment_number}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default ExperimentsPage;
