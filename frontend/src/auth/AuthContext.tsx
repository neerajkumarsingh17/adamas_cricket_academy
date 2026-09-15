import { createContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, setAccessToken, setRefreshHandler, type Me, type TokenPair } from '../api/client'

export const REFRESH_TOKEN_KEY = 'aca_oms_refresh_token'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export interface AuthContextValue {
  me: Me | null
  status: AuthStatus
  login: (loginId: string, password: string) => Promise<void>
  loginWithOtp: (mobile: string, otp: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

async function refreshFromStorage(): Promise<boolean> {
  const stored = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!stored) return false
  try {
    const tokens = await authApi.refresh(stored)
    setAccessToken(tokens.access)
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh)
    return true
  } catch {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    setAccessToken(null)
    return false
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  useEffect(() => {
    // A reused refresh token is rejected by the backend (rotation +
    // blacklist-on-reuse) — the 401-triggered retry in client.ts calls
    // back into this same function for any request made after the access
    // token in memory expires, not just on first load.
    setRefreshHandler(refreshFromStorage)

    let cancelled = false
    void (async () => {
      const ok = await refreshFromStorage()
      if (!ok) {
        if (!cancelled) setStatus('unauthenticated')
        return
      }
      try {
        const meData = await authApi.me()
        if (!cancelled) {
          setMe(meData)
          setStatus('authenticated')
        }
      } catch {
        if (!cancelled) setStatus('unauthenticated')
      }
    })()

    return () => {
      cancelled = true
      setRefreshHandler(null)
    }
  }, [])

  async function establishSession(tokens: TokenPair) {
    setAccessToken(tokens.access)
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh)
    const meData = await authApi.me()
    setMe(meData)
    setStatus('authenticated')
  }

  async function login(loginId: string, password: string) {
    const tokens = await authApi.login({ login_id: loginId, password })
    await establishSession(tokens)
  }

  async function loginWithOtp(mobile: string, otp: string) {
    const tokens = await authApi.verifyOtp({ mobile, otp })
    await establishSession(tokens)
  }

  async function logout() {
    const stored = localStorage.getItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    setAccessToken(null)
    setMe(null)
    setStatus('unauthenticated')
    if (stored) {
      try {
        await authApi.logout(stored)
      } catch {
        // Best-effort — the client-side session is already cleared either way.
      }
    }
  }

  return (
    <AuthContext.Provider value={{ me, status, login, loginWithOtp, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
