import { createContext, useEffect, useState } from 'react'
import { getCurrentUser } from '../services/authService'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const restoreSession = async () => {
      if (!localStorage.getItem('access_token')) {
        setIsLoading(false)
        return
      }
      try {
        const { data } = await getCurrentUser()
        setUser(data)
      } catch {
        localStorage.removeItem('access_token')
      } finally {
        setIsLoading(false)
      }
    }
    restoreSession()
  }, [])

  const signIn = ({ access_token, user: loggedInUser }) => {
    localStorage.setItem('access_token', access_token)
    setUser(loggedInUser)
  }

  const signOut = () => {
    localStorage.removeItem('access_token')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>{children}</AuthContext.Provider>
}
