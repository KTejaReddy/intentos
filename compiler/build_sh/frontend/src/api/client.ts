// Generated API client
export const API_BASE = (window as any).INTENTOS_API || ''

export async function request(
  method: string,
  path: string,
  body?: any,
  params?: Record<string, any>
): Promise<any> {
  const qs = params
    ? '?' + new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null) as any
      ).toString()
    : ''
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('intentos_token')
  if (token) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(API_BASE + path + qs, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* ignore */ }
    const err: any = new Error(detail)
    err.detail = detail
    err.status = res.status
    throw err
  }
  return res.json()
}

export function toast(message: string) {
  let host = document.getElementById('toast-host')
  if (!host) {
    host = document.createElement('div')
    host.id = 'toast-host'
    document.body.appendChild(host)
  }
  const el = document.createElement('div')
  el.className = 'toast'
  el.textContent = message
  host.appendChild(el)
  setTimeout(() => el.remove(), 3200)
}
