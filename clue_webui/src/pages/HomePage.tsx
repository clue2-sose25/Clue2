import { useEffect, useState } from "react";
import {
  PauseIcon,
  ClockIcon,
  FilesIcon,
  RocketLaunchIcon,
  StackIcon,
} from "@phosphor-icons/react";
import Card from "../components/Card";

const HomePage = () => {
  const [statusText, setStatusText] = useState<string>("Loading...");
  const [isDeploying, setIsDeploying] = useState<boolean | null>(null);
  const [queueCount, setQueueCount] = useState<number>(0);
  const [resultsCount, setResultsCount] = useState<number>(0);

  useEffect(() => {
    fetch("/api/status")
      .then((res) => res.json())
      .then((data) => {
        if (data && typeof data.is_deploying === "boolean") {
          setStatusText(
            data.is_deploying ? "Deploying..." : "Waiting for deployments"
          );
          setIsDeploying(data.is_deploying);
        } else {
          setStatusText("Unknown");
          setIsDeploying(null);
        }
      })
      .catch(() => {
        setStatusText("Unavailable");
        setIsDeploying(null);
      });

    fetch("/api/queue")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setQueueCount(data.length);
        } else {
          setQueueCount(0);
        }
      })
      .catch(() => setQueueCount(0));

    // Fetch the number of results
    fetch("/api/results")
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data)) {
          setResultsCount(data.length);
        } else {
          setResultsCount(0);
        }
      })
      .catch(() => setResultsCount(0));
  }, []);

  const statusIcon =
    isDeploying === null ? (
      <ClockIcon size={60} />
    ) : isDeploying ? (
      <RocketLaunchIcon size={60} />
    ) : (
      <PauseIcon size={60} />
    );

  return (
    <div className="w-full h-full flex justify-center">
      <div className="pt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
        <Card
          title="EXPERIMENTS QUEUE"
          icon={<StackIcon size={60} />}
          text={
            queueCount === 0
              ? "The queue is empty"
              : `${queueCount} experiments in the queue`
          }
          subText={queueCount === 0 ? "" : "Estimated time: -"}
          link="/control"
          button="Add a new experiment"
        />
        <Card
          title="DEPLOYER STATUS"
          icon={statusIcon}
          text={statusText}
          link="/dashboard"
          button="View the dashboard"
        />
        <Card
          title="RESULTS"
          icon={<FilesIcon size={60} />}
          text={`Results: ${resultsCount}`}
          link="/results"
          button="View all results"
        />
      </div>
    </div>
  );
};

export default HomePage;
