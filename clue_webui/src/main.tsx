import {StrictMode} from "react";
import {createRoot} from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import {BrowserRouter} from "react-router";
import {DeploymentProvider} from "./contexts/DeploymentContext.tsx";
import {QueueProvider} from "./contexts/QueueContext.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <QueueProvider>
        <DeploymentProvider>
          <App />
        </DeploymentProvider>
      </QueueProvider>
    </BrowserRouter>
  </StrictMode>
);
