import {DownloadSimpleIcon, RepeatIcon, TrashIcon} from "@phosphor-icons/react";
import React, {useEffect, useState} from "react";
import {Link} from "react-router";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
} from "@mui/material";
import type {ResultEntry} from "../models/ResultEntry";

const ExperimentsResultsPage = () => {
  const [results, setResults] = useState<ResultEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = await fetch(`/api/results/${id}`, {method: "DELETE"});
      if (!res.ok) throw new Error("Failed to delete");
      setResults((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetch("/api/results")
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

  if (loading) return <div>Loading results...</div>;

  if (error || !results || results.length === 0) {
    return (
      <div>No experiments found. Deploy an experiment to see its results.</div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col gap-6 p-6 pt-4">
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <p className="font-semibold">Timestamp</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Workload</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Branch</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Iterations</p>
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((result) => (
              <TableRow
                key={result.id}
                component={Link}
                to={`/results/${result.id}`}
                style={{textDecoration: "none", color: "inherit"}}
                hover
              >
                <TableCell>{result.timestamp}</TableCell>
                <TableCell>{result.workload}</TableCell>
                <TableCell>{result.branch_name}</TableCell>
                <TableCell>{result.iterations}</TableCell>
                <TableCell>
                  {/** Icons */}
                  <Tooltip title="Repeat experiment" arrow placement="top">
                    <IconButton onClick={() => {}}>
                      <RepeatIcon size={20} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Download results" arrow placement="top">
                    <IconButton onClick={() => {}}>
                      <DownloadSimpleIcon size={20} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete results" arrow placement="top">
                    <IconButton onClick={(e) => handleDelete(result.id, e)}>
                      <TrashIcon size={20} color="red" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
};

export default ExperimentsResultsPage;
