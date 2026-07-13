import { Routes, Route } from 'react-router-dom';
import PatientChat from './PatientChat';
import HospitalDashboard from './HospitalDashboard';
import HospitalSession from './HospitalSession';
import ResourceMapDashboard from './ResourceMapDashboard';

function App() {
  return (
    <Routes>
      <Route path="/" element={<PatientChat />} />
      <Route path="/hospital" element={<HospitalDashboard />} />
      <Route path="/hospital/session/:session_id" element={<HospitalSession />} />
      <Route path="/hospital/map" element={<ResourceMapDashboard />} />
    </Routes>
  );
}

export default App;
