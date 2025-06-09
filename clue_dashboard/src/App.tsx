import {Route, Routes} from "react-router";
import ControlsPage from "./pages/ControlsPage";
import ResultsPage from "./pages/ResultsPage";
import BenchmarksPage from "./pages/BenchmarksPage";
import Navbar from "./components/Navbar";
import LogsPage from "./pages/LogsPage";

function App() {
  return (
    <div className="w-full h-full">
      <Navbar />
      <div className="p-4">
        <Routes>
          <Route path="/" element={<ControlsPage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/benchmarks" element={<BenchmarksPage />} />
          <Route path="/logs" element={<LogsPage />} />   
        </Routes>
      </div>
    </div>
  );
}

export default App;
