import {createContext, useState} from "react";
import type {ReactNode} from "react";
import type {DeploymentForm} from "../models/DeploymentForm";

// Define the context type
interface QueueContextType {
  currentQueue: DeploymentForm[];
  setCurrentQueue: React.Dispatch<React.SetStateAction<DeploymentForm[]>>;
  queueSize: number;
  setQueueSize: React.Dispatch<React.SetStateAction<number>>;
}
// Create context with undefined as initial value to enforce provider usage
export const QueueContext = createContext<QueueContextType>({
  currentQueue: [],
  setCurrentQueue: () => null,
  queueSize: 0,
  setQueueSize: () => null,
});

// Context provider
export const QueueProvider = ({children}: {children: ReactNode}) => {
  const [currentQueue, setCurrentQueue] = useState<DeploymentForm[]>([]);
  const [queueSize, setQueueSize] = useState<number>(0);

  const value: QueueContextType = {
    currentQueue,
    setCurrentQueue,
    queueSize,
    setQueueSize,
  };

  return (
    <QueueContext.Provider value={value}>{children}</QueueContext.Provider>
  );
};
