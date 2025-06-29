import {
  ArrowLeftIcon,
  DownloadSimpleIcon,
  RepeatIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
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
import type { ResultEntry } from "../models/ResultEntry";

const ResultsPage = () => {
  const [results, setResults] = useState<ResultEntry[]>([]);
  const navigate = useNavigate();

  const handleDelete = async (uuid: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = await fetch(`/api/results/${uuid}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      setResults((prev) => prev.filter((r) => r.uuid !== uuid));
    } catch (err) {
      console.error(err);
    }
  };

  const handleRowClick = (uuid: string) => {
    navigate(`/results/${uuid}`);
  };

  useEffect(() => {
    fetch("/api/results")
      .then((res) => {
        if (!res.ok) throw new Error("Request failed");
        return res.json();
      })
      .then((data) => {
        setResults(data);
      })
      .catch(() => { });
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "STARTED":
        return "!text-orange-500";
      case "FAILED":
        return "!text-red-600";
      case "COMPLETED":
        return "!text-green-600";
      default:
        return "!text-gray-700";
    }
  };

  return (
    <div className="w-full h-full flex flex-col gap-6 p-6 pt-4">
      <div className="flex justify-between items-center">
        <Link
          to="/"
          className="flex gap-2 items-center text-sm text-gray-600 hover:underline"
        >
          <ArrowLeftIcon /> Back
        </Link>
      </div>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>
                <p className="font-semibold">SUT</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">TIMESTAMP</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">VARIANTS</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">WORKLOADS</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">ITERATIONS</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">STATUS</p>
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results && results.map((result) => (
              <TableRow
                key={result.uuid}
                hover
                style={{ cursor: "pointer" }}
                onClick={() => handleRowClick(result.uuid)}
              >
                <TableCell>{result.sut}</TableCell>
                <TableCell>{result.timestamp}</TableCell>
                <TableCell>{result.variants}</TableCell>
                <TableCell>{result.workloads}</TableCell>
                <TableCell>{result.n_iterations}</TableCell>
                <TableCell className={getStatusColor(result.status)}>{result.status}</TableCell>
                <TableCell>
                  {/** Icons */}
                  <Tooltip title="Repeat experiment" arrow placement="top">
                    <IconButton onClick={(e) => { e.stopPropagation(); }}>
                      <RepeatIcon size={20} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Download results" arrow placement="top">
                    <IconButton onClick={(e) => { e.stopPropagation(); }}>
                      <DownloadSimpleIcon size={20} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete results" arrow placement="top">
                    <IconButton onClick={(e) => handleDelete(result.uuid, e)}>
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

export default ResultsPage;