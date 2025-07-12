import {useState, useEffect, useRef} from "react";
import type {ResultDetails} from "../../models/ResultsDetails";

const ResultsServerFrame: React.FC<{data: ResultDetails}> = ({data}) => {
  const [isServerReady, setIsServerReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const serverStartedRef = useRef(false);

  useEffect(() => {
    let intervalId: number;
    let isServerReadyRef = false;

    const startResultsServer = async () => {
      // Prevent multiple server starts
      if (serverStartedRef.current) {
        return;
      }

      serverStartedRef.current = true;
      console.log("Starting server for:", data.id, data.sut);

      try {
        await fetch("/api/results/startResultsServer", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            uuid: data.id,
            sut_name: data.sut,
          }),
        });
      } catch (error) {
        console.error("Failed to start results server:", error);
        serverStartedRef.current = false; // Reset on error
      }
    };

    const checkServerStatus = async () => {
      try {
        await fetch("http://localhost:8050", {
          method: "HEAD",
          mode: "no-cors", // This prevents CORS issues when checking availability
        });
        isServerReadyRef = true;
        setIsServerReady(true);
        setIsLoading(false);
        clearInterval(intervalId);
      } catch (error) {
        setIsServerReady(false);
        setIsLoading(false);
      }
    };

    // Start the server first
    startResultsServer();

    // Check immediately
    checkServerStatus();

    // Then check every 2 seconds until server is ready
    intervalId = setInterval(() => {
      if (!isServerReadyRef) {
        checkServerStatus();
      }
    }, 2000);

    return () => clearInterval(intervalId);
  }, [data.id, data.sut]);

  if (isLoading || !isServerReady) {
    return (
      <div className="h-[600px] flex items-center justify-center bg-gray-50 border border-gray-200 rounded-lg">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            The results server is being deployed
          </h3>
          <p className="text-gray-500">
            Please wait while we start the server...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[600px]">
      <iframe
        src="http://localhost:8050"
        width="100%"
        height="100%"
        className="border-none"
        title="Results server"
      />
    </div>
  );
};

export default ResultsServerFrame;
