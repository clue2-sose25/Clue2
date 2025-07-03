import ExperimentPage from "./pages/ExperimentPage";
import Navbar from "./components/Navbar";
import {Route, Routes} from "react-router";
import ResultPage from "./pages/ResultPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import ClusterConfigPage from "./pages/SettingsPage";
import ResultsPage from "./pages/ResultsPage";
import AddSutPage from "./pages/AddSutPage";

function App() {
  return (
    <div className="w-full h-full">
      <Navbar />
      <div className="p-4 w-full h-[calc(100vh-64px)] bg-gray-50">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/experiment" element={<ExperimentPage />} />
          <Route path="/experiment/add-sut" element={<AddSutPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/results/:uuid" element={<ResultPage />} />
          <Route path="/settings" element={<ClusterConfigPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
