import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { get, patch, post } from '../api/client'
import type { User } from '../types/api'
import { applyLanguage } from '../i18n'

type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (full_name: string, email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  refreshUser: () => Promise<User | null>
  updateProfile: (full_name: string, email: string) => Promise<User>
  updateLanguage: (language: 'en' | 'ar') => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    try {
      const current = await get<User>('/api/me')
      setUser(current)
      applyLanguage(current.preferred_language || 'en')
      return current
    } catch {
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refreshUser() }, [])

  const login = async (email: string, password: string) => {
    const response = await post<{ user: User }>('/api/auth/login', { email, password })
    setUser(response.user)
    applyLanguage(response.user.preferred_language || 'en')
    return response.user
  }

  const register = async (full_name: string, email: string, password: string) => {
    const response = await post<{ user: User }>('/api/auth/register', { full_name, email, password })
    setUser(response.user)
    applyLanguage(response.user.preferred_language || 'en')
    return response.user
  }

  const logout = async () => {
    try { await post('/api/auth/logout') } finally { setUser(null) }
  }

  const updateProfile = async (full_name: string, email: string) => {
    const updated = await patch<User>('/api/auth/me', { full_name, email })
    setUser(updated)
    return updated
  }

  const updateLanguage = async (language: 'en' | 'ar') => {
    applyLanguage(language)
    if (!user) return
    try {
      const updated = await patch<User>('/api/auth/preferences', { preferred_language: language })
      setUser(updated)
    } catch {
      setUser({ ...user, preferred_language: language })
    }
  }

  const value = useMemo<AuthContextValue>(() => ({ user, loading, login, register, logout, refreshUser, updateProfile, updateLanguage }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
