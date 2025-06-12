import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import {BrowserRouter} from "react-router";
import {DeploymentProvider} from "./contexts/DeploymentContext.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <DeploymentProvider>
        <App />
      </DeploymentProvider>
    </BrowserRouter>
  </StrictMode>
);
