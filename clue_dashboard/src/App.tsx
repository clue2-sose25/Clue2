import ControlsPage from "./pages/ControlsPage";
import Navbar from "./components/Navbar";
import {Route, Routes} from "react-router";
import ExperimentsResultsPage from "./pages/ExperimentsResultsPage";
import ResultPage from "./pages/ResultPage";

function App() {
  return (
    <div className="w-full h-full">
      <Navbar />
      <div className="p-4">
        <Routes>
          <Route path="/" element={<ControlsPage />} />
          <Route path="/results" element={<ExperimentsResultsPage />} />
          <Route path="/results/:id" element={<ResultPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
