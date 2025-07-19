import {createContext, useState} from "react";
import type {ReactNode} from "react";
import type {DeploymentForm} from "../models/DeploymentForm";

// Define default form values
const defaultDeploymentForm: DeploymentForm = {
  sut: null,
  variants: [],
  workloads: [],
  iterations: 1,
  deploy_only: false,
};

// Define context shape
type DeploymentContextType = {
  currentDeployment: DeploymentForm;
  setCurrentDeployment: React.Dispatch<React.SetStateAction<DeploymentForm>>;
  ifDeploying: boolean;
  setIfDeploying: React.Dispatch<React.SetStateAction<boolean>>;
};

// Create context with sensible defaults
export const DeploymentContext = createContext<DeploymentContextType>({
  currentDeployment: defaultDeploymentForm,
  setCurrentDeployment: () => null,
  ifDeploying: false,
  setIfDeploying: () => null,
});

// Context provider
export const DeploymentProvider = ({children}: {children: ReactNode}) => {
  const [currentDeployment, setCurrentDeployment] = useState<DeploymentForm>(
    defaultDeploymentForm
  );
  const [ifDeploying, setIfDeploying] = useState<boolean>(false);

  const value: DeploymentContextType = {
    currentDeployment,
    setCurrentDeployment,
    ifDeploying,
    setIfDeploying,
  };

  return (
    <DeploymentContext.Provider value={value}>
      {children}
    </DeploymentContext.Provider>
  );
};
