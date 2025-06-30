import ControlsPage from "./pages/ControlsPage";
import Navbar from "./components/Navbar";
import {Route, Routes} from "react-router";
import ExperimentsResultsPage from "./pages/ExperimentsResultsPage";
import ResultPage from "./pages/ResultPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import ClusterConfigPage from "./pages/ClusterConfigPage";


function App() {
  return (
    <div className="w-full h-full">
      <Navbar />
      <div className="p-4">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/control" element={<ControlsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/results" element={<ExperimentsResultsPage />} />
          <Route path="/results/:resultEntryId" element={<ResultPage />} />
          <Route path="/cluster" element={<ClusterConfigPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
