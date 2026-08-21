import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  if (isLoading) 
    return <p className="page-status">Loading session…</p>
  return user ? <Outlet /> : <Navigate to="/login" replace />
}
