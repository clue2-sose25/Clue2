import ControlsPage from "./pages/ControlsPage";
import Navbar from "./components/Navbar";
import {Route, Routes} from "react-router";
import ExperimentsResultsPage from "./pages/ExperimentsResultsPage";
import ResultPage from "./pages/ResultPage";
import DashboardPage from "./pages/DashboardPage";

function App() {
  return (
    <div className="w-full h-full">
      <Navbar />
      <div className="p-4">
        <Routes>
          <Route path="/" element={<ControlsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/results" element={<ExperimentsResultsPage />} />
          <Route path="/results/:resultEntryId" element={<ResultPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
