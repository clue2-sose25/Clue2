import {createContext, useState} from "react";
import type {ReactNode} from "react";
import type {DeploymentForm} from "../models/DeploymentForm";

// Define the context type
interface QueueContextType {
  currentQueue: DeploymentForm[];
  setCurrentQueue: React.Dispatch<React.SetStateAction<DeploymentForm[]>>;
}

// Create context with undefined as initial value to enforce provider usage
export const QueueContext = createContext<QueueContextType>({
  currentQueue: [],
  setCurrentQueue: () => null,
});

// Context provider
export const QueueProvider = ({children}: {children: ReactNode}) => {
  const [currentQueue, setCurrentQueue] = useState<DeploymentForm[]>([]);

  const value: QueueContextType = {
    currentQueue,
    setCurrentQueue,
  };

  return (
    <QueueContext.Provider value={value}>{children}</QueueContext.Provider>
  );
};
