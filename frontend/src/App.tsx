import { Navigate, Route, Routes } from "react-router-dom";
import InputPage from "./pages/InputPage";
import HistoryPage from "./pages/HistoryPage";
import Workspace from "./pages/Workspace";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<InputPage />} />
      <Route path="/history" element={<HistoryPage />} />
      <Route path="/analysis/:id/*" element={<Workspace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
