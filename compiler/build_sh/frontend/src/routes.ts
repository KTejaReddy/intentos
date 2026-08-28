// Page name -> hash route map (generated)
export const ROUTES: Record<string, string> = {
  "Login": "/login",
  "Dashboard": "/dashboard",
}

export function go(page: string) {
  const r = ROUTES[page]
  if (r) window.location.hash = '#' + r
}
