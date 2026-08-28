// @ts-nocheck
import { useEffect, useState } from 'react'
import ROUTES from './pages'

export default function App() {
  const getRoute = () => window.location.hash.replace(/^#/, '') || '/'
  const [route, setRoute] = useState(getRoute())
  useEffect(() => {
    const onHash = () => setRoute(getRoute())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  const Page = ROUTES[route] || ROUTES['/']
  if (!Page) return <div className='page'>Not found</div>
  return <Page />
}
