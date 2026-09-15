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
import CompaniesPage from './pages/SuperAdmin/CompaniesPage'
import CreateCompanyPage from './pages/SuperAdmin/CreateCompanyPage'
import CompanyDetailsPage from './pages/SuperAdmin/CompanyDetailsPage'
import SuperAdminAnalyticsPage from './pages/SuperAdmin/SuperAdminAnalyticsPage'
import SuperAdminCustomizationRequestsPage from './pages/SuperAdmin/SuperAdminCustomizationRequestsPage'
import CompanyProfilePage from './pages/Admin/CompanyProfilePage'
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
          <Route path="/issues/:id" element={<ReportedIssuesPage />} />
          <Route path="/sprints" element={<SprintPlanningPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/employees" element={<EmployeeManagementPage />} />
          <Route path="/teams" element={<TeamManagementPage />} />
          <Route path="/team-management" element={<Navigate to="/teams" replace />} />
          
          {/* Super Admin Platform Routes */}
          <Route path="/super-admin/companies" element={<CompaniesPage />} />
          <Route path="/super-admin/companies/create" element={<CreateCompanyPage />} />
          <Route path="/super-admin/companies/:id" element={<CompanyDetailsPage />} />
          <Route path="/super-admin/analytics" element={<SuperAdminAnalyticsPage />} />
          <Route path="/super-admin/customization-requests" element={<SuperAdminCustomizationRequestsPage />} />

          {/* Company Admin & Tenant Settings Routes */}
          <Route path="/company/profile" element={<CompanyProfilePage />} />
          <Route path="/company/customization-requests" element={<CompanyProfilePage initialTab="requests" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
