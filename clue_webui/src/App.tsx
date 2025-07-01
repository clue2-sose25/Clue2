import ExperimentPage from "./pages/ExperimentPage";
import Navbar from "./components/Navbar";
import { Route, Routes } from "react-router";
import ResultsPage from "./pages/ResultsPage";
import ResultPage from "./pages/ResultPage";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";

function App() {
  return (
    <div className="w-full h-full">
      <Navbar />
      <div className="p-4 w-full h-[calc(100vh-64px)] bg-gray-50">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/experiment" element={<ExperimentPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/results/:uuid" element={<ResultPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
