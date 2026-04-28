import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { TeacherView } from './pages/TeacherView';
import { DisplayView } from './pages/DisplayView';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/teacher" replace />} />
        <Route path="/teacher" element={<TeacherView />} />
        <Route path="/display" element={<DisplayView />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
