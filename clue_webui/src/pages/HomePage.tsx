import { useEffect, useState } from "react";
import type { ReactElement } from "react";
import { Link } from "react-router";
import { PauseIcon, ClockIcon, FilesIcon, RocketLaunchIcon } from "@phosphor-icons/react";

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

    fetch("/api/results")
      .then((res) => res.json())
      .then((data) => {
        if (data && Array.isArray(data.results)) {
          setResultsCount(data.results.length);
        } else {
          setResultsCount(0);
        }
      })
      .catch(() => setResultsCount(0));
  }, []);

  const Card = ({
    title,
    icon,
    text,
    subText,
    link,
    button,
  }: {
    title: string;
    icon: ReactElement;
    text: string;
    subText?: string;
    link: string;
    button: string;
  }) => (
    <div className="w-72 h-72 bg-white rounded-xl shadow-md hover:shadow-lg transition flex flex-col justify-between p-6">
      <div className="flex flex-col items-center gap-2">
        <div>{icon}</div>
        <div className="text-xs text-gray-500 font-medium">{title}</div>
        <div className="text-center font-semibold text-lg">{text}</div>
        {subText && <div className="text-xs text-gray-500 text-center">{subText}</div>}
      </div>
      <Link
        to={link}
        className="mt-4 bg-blue-500 text-white rounded px-3 py-2 text-sm text-center hover:bg-blue-700"
      >
        {button}
      </Link>
    </div>
  );

  const statusIcon =
    isDeploying === null ? (
      <ClockIcon size={40} />
    ) : isDeploying ? (
      <RocketLaunchIcon size={40} />
    ) : (
      <PauseIcon size={40} />
    );

  return (
    <div className="w-full h-full flex justify-center">
      <div className="pt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
        <Card
          title="STATUS"
          icon={statusIcon}
          text={statusText}
          link="/dashboard"
          button="View dashboard"
        />
        <Card
          title="EXPERIMENTS QUEUE"
          icon={<ClockIcon size={40} />}
          text={queueCount === 0 ? "No experiments in the queue" : `${queueCount} experiments waiting`}
          subText="Estimated time: XXX"
          link="/control"
          button="Add new experiment"
        />
        <Card
          title="RESULTS"
          icon={<FilesIcon size={40} />}
          text={`${resultsCount} run${resultsCount === 1 ? "" : "s"}`}
          link="/results"
          button="View results"
        />
      </div>
    </div>
  );
};

export default HomePage;