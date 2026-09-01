import { Navigate } from 'react-router-dom'

export default function RegisterPage() {
  // Public self-registration has been disabled in BugForge.
  // Only administrators can provision employee accounts.
  return <Navigate to="/login" replace />
}
