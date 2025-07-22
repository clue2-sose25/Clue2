import {
  ArrowLeftIcon,
  DownloadSimpleIcon,
  RepeatIcon,
  TrashIcon,
} from "@phosphor-icons/react";
import React, {useContext, useEffect, useState} from "react";
import {Link, useNavigate} from "react-router";
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
import {parse, format} from "date-fns";
import {DeploymentContext} from "../contexts/DeploymentContext";
import {QueueContext} from "../contexts/QueueContext";

const ResultsPage = () => {
  const {setIfDeploying} = useContext(DeploymentContext);

  const {setCurrentQueue} = useContext(QueueContext);

  const [results, setResults] = useState<ResultEntry[]>([]);
  const navigate = useNavigate();

  const handleDelete = async (uuid: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = await fetch(`/api/results/${uuid}`, {method: "DELETE"});
      if (!res.ok) throw new Error("Failed to delete");
      setResults((prev) => prev.filter((r) => r.uuid !== uuid));
    } catch (err) {
      console.error(err);
    }
  };

  const fetchQueue = () => {
    fetch("/api/queue")
      .then(async (r) => {
        if (!r.ok) {
          throw new Error(`API responded with status ${r.status}`);
        }
        const data = await r.json();
        // Validate data type (optional, adjust based on your needs)
        if (!Array.isArray(data)) {
          console.error("API returned non-array data:", data);
          return [];
        }
        return data;
      })
      .then((d) => setCurrentQueue(d ?? []))
      .catch((err) => {
        console.error("Failed to fetch queue:", err);
        setCurrentQueue([]);
      });
  };

  const handleRepeatExperiment = async (
    result: ResultEntry,
    e: React.MouseEvent
  ) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const response = await fetch("/api/deploy/sut", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          sut: result.sut,
          variants: result.variants,
          workloads: result.workloads,
          n_iterations: result.n_iterations,
          deploy_only: result.deploy_only,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to repeat experiment");
      }
      // If you have these functions available, uncomment:
      setIfDeploying(true);
      fetchQueue();
      navigate("/dashboard");
    } catch (err) {
      console.error("Error repeating experiment:", err);
    }
  };

  const handleResultsDownload = async (uuid: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const res = await fetch(`/api/results/${uuid}/download`);
      if (!res.ok) throw new Error("Failed to download");

      // Convert response to blob
      const blob = await res.blob();

      // Create download URL and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `results-${uuid}.zip`; // Set filename
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
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
      .catch(() => {});
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "STARTED":
        return "!text-orange-500";
      case "FAILED":
        return "!text-red-600";
      case "STOPPED":
        return "!text-red-500";
      case "SUCCESS":
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
                <p className="font-semibold">Timestamp</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Variants</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Workloads</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Iterations No.</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Deploy Only</p>
              </TableCell>
              <TableCell>
                <p className="font-semibold">Experiment Status</p>
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results &&
              results.map((result) => (
                <TableRow
                  key={result.uuid}
                  hover
                  style={{cursor: "pointer"}}
                  onClick={() => handleRowClick(result.uuid)}
                >
                  <TableCell>
                    <div className="capitalize">{result.sut}</div>
                  </TableCell>
                  <TableCell>
                    {format(
                      parse(
                        result.timestamp,
                        "yyyy-MM-dd_HH-mm-ss",
                        new Date()
                      ),
                      "PPpp"
                    )}
                  </TableCell>
                  <TableCell>{result.variants.split(",").join(", ")}</TableCell>
                  <TableCell>
                    {result.workloads.split(",").join(", ")}
                  </TableCell>
                  <TableCell>{result.n_iterations}</TableCell>
                  <TableCell>{result.deploy_only ? "True" : "False"}</TableCell>
                  <TableCell className={getStatusColor(result.status)}>
                    {result.status}
                  </TableCell>
                  <TableCell>
                    {/** Icons */}
                    <Tooltip title="Repeat experiment" arrow placement="top">
                      <IconButton
                        onClick={(e) => {
                          handleRepeatExperiment(result, e);
                        }}
                      >
                        <RepeatIcon size={20} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Download results" arrow placement="top">
                      <IconButton
                        onClick={(e) => {
                          handleResultsDownload(result.uuid, e);
                        }}
                      >
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
