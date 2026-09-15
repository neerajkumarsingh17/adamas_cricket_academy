// Typed fetch wrapper. Request/response shapes come from ./types.gen.ts,
// generated from the backend's OpenAPI schema (docs/06-conventions.md —
// "Never hand-edit that file"; run `npm run generate:api` after a
// serializer change).
import type { components } from './types.gen'

const API_BASE = '/api/v1'

export interface ErrorEnvelope {
  code: string
  message: string
  field_errors: Record<string, string[]>
  request_id: string
}

export class ApiError extends Error {
  status: number
  code: string
  fieldErrors: Record<string, string[]>
  requestId: string

  constructor(status: number, body: ErrorEnvelope) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.fieldErrors = body.field_errors
    this.requestId = body.request_id
  }
}

// The in-memory access token, set on login/refresh and cleared on logout.
// Not persisted directly — AuthProvider persists the *refresh* token and
// uses it to obtain a fresh access token on page load.
let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

// AuthProvider registers this so a 401 can trigger one silent refresh +
// retry, without client.ts importing React state (would be circular:
// AuthProvider itself calls into this module).
type RefreshHandler = () => Promise<boolean>
let refreshHandler: RefreshHandler | null = null

export function setRefreshHandler(fn: RefreshHandler | null) {
  refreshHandler = fn
}

export async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (response.status === 401 && !isRetry && refreshHandler) {
    const refreshed = await refreshHandler()
    if (refreshed) return request<T>(path, init, true)
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorEnvelope | null
    throw new ApiError(
      response.status,
      body ?? { code: 'error', message: response.statusText, field_errors: {}, request_id: '' },
    )
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

// For endpoints that return a file (ID card / trial-sheet PDFs) rather
// than JSON — a plain `<a href>` can't carry the Bearer token, so this
// fetches the bytes under the same auth as every other request and hands
// back a blob: URL the caller opens/downloads itself.
export async function requestBlob(path: string, init?: RequestInit, isRetry = false): Promise<Blob> {
  const headers = new Headers(init?.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (response.status === 401 && !isRetry && refreshHandler) {
    const refreshed = await refreshHandler()
    if (refreshed) return requestBlob(path, init, true)
  }

  if (!response.ok) {
    throw new ApiError(response.status, {
      code: 'error',
      message: response.statusText,
      field_errors: {},
      request_id: '',
    })
  }
  return response.blob()
}

export type LoginRequest = components['schemas']['Login']
export type TokenPair = components['schemas']['TokenPair']
export type OTPRequestBody = components['schemas']['OTPRequest']
export type OTPRequestResponse = components['schemas']['OTPRequestResponse']
export type OTPVerifyBody = components['schemas']['OTPVerify']
export type Me = components['schemas']['Me']
export type Dashboard = components['schemas']['Dashboard']
export type DashboardTile = components['schemas']['DashboardTile']
export type DashboardCard = components['schemas']['DashboardCard']

export const authApi = {
  login: (body: LoginRequest) =>
    request<TokenPair>('/auth/login/', { method: 'POST', body: JSON.stringify(body) }),

  requestOtp: (body: OTPRequestBody) =>
    request<OTPRequestResponse>('/auth/otp/request/', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  verifyOtp: (body: OTPVerifyBody) =>
    request<TokenPair>('/auth/otp/verify/', { method: 'POST', body: JSON.stringify(body) }),

  // ROTATE_REFRESH_TOKENS is on (config/settings/base.py) — the response
  // carries a new refresh token too, and the old one is blacklisted.
  refresh: (refresh: string) =>
    request<TokenPair>('/auth/refresh/', { method: 'POST', body: JSON.stringify({ refresh }) }),

  logout: (refresh: string) =>
    request<void>('/auth/logout/', { method: 'POST', body: JSON.stringify({ refresh }) }),

  me: () => request<Me>('/auth/me/'),
}

export const dashboardApi = {
  // Role is resolved server-side from the caller's own token — there is
  // no parameter here for a role, by design (docs: a coach can't ask for
  // another role's payload).
  me: () => request<Dashboard>('/dashboards/me/'),
}
