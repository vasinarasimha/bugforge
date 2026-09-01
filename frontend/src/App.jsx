import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './routes/ProtectedRoute'
import HomePage from './pages/Home/HomePage'
import LoginPage from './pages/Auth/LoginPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import AnalyticsPage from './pages/Analytics/AnalyticsPage'
import ProjectsPage from './pages/Projects/ProjectsPage'
import ReportedIssuesPage from './pages/Issues/ReportedIssuesPage'
import SprintPlanningPage from './pages/Sprints/SprintPlanningPage'
import ProfilePage from './pages/Profile/ProfilePage'
import EmployeeManagementPage from './pages/Admin/EmployeeManagementPage'
import TeamManagementPage from './pages/Admin/TeamManagementPage'
import DashboardLayout from './layouts/DashboardLayout'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      {/* Self-registration route disabled and redirected to login */}
      <Route path="/register" element={<Navigate to="/login" replace />} />
      
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/issues" element={<ReportedIssuesPage />} />
          <Route path="/sprints" element={<SprintPlanningPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/employees" element={<EmployeeManagementPage />} />
          <Route path="/teams" element={<TeamManagementPage />} />
          <Route path="/team-management" element={<Navigate to="/teams" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
