import ControlsPage from "./pages/ControlsPage";
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
      <div className="p-4">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/control" element={<ControlsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/results/:uuid" element={<ResultPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
