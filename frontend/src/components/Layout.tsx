import { useQuery } from '@tanstack/react-query'
import { Activity, Gavel, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { fetchHealth, triggerScrape } from '../api/client'

export default function Layout() {
  const [scraping, setScraping] = useState(false)
  const [scrapeMsg, setScrapeMsg] = useState<string | null>(null)

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 60_000,
  })

  async function handleScrape() {
    const key = import.meta.env.VITE_SCRAPE_API_KEY as string | undefined
    if (!key) {
      setScrapeMsg('Configura VITE_SCRAPE_API_KEY para activar el scraping manual.')
      return
    }
    setScraping(true)
    setScrapeMsg(null)
    try {
      const res = await triggerScrape(key)
      setScrapeMsg(`Tarea iniciada: ${res.task_id.slice(0, 8)}…`)
    } catch (e) {
      setScrapeMsg('Error al iniciar el scraping.')
    } finally {
      setScraping(false)
      setTimeout(() => setScrapeMsg(null), 5000)
    }
  }

  const dbOk = health?.database === 'ok'
  const redisOk = health?.redis === 'ok'

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top navbar */}
      <header className="bg-slate-900 border-b border-slate-700/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center gap-6">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 text-amber-500 font-bold text-lg shrink-0">
            <Gavel className="w-5 h-5" />
            <span>Valencia Subastas</span>
          </Link>

          {/* Nav links */}
          <nav className="flex gap-1">
            <NavLink
              to="/oportunidades"
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700/50'
                }`
              }
            >
              <span className="flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4" />
                Oportunidades
              </span>
            </NavLink>
            <NavLink
              to="/subastas"
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-700/50'
                }`
              }
            >
              <span className="flex items-center gap-1.5">
                <Gavel className="w-4 h-4" />
                Subastas
              </span>
            </NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-4">
            {/* Health indicators */}
            <div className="hidden sm:flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${dbOk ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="text-slate-400">BD</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${redisOk ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="text-slate-400">Redis</span>
              </span>
              {health?.active_auctions !== undefined && (
                <span className="text-slate-500">
                  <span className="text-slate-300 font-medium">{health.active_auctions}</span> activas
                </span>
              )}
            </div>

            {/* Scrape button */}
            <button
              onClick={handleScrape}
              disabled={scraping}
              className="btn-primary flex items-center gap-1.5 text-sm"
            >
              <Activity className={`w-4 h-4 ${scraping ? 'animate-pulse' : ''}`} />
              {scraping ? 'Scrapeando…' : 'Scrape ahora'}
            </button>
          </div>
        </div>

        {/* Toast feedback */}
        {scrapeMsg && (
          <div className="bg-slate-700 border-t border-slate-600 text-center text-xs py-1.5 text-slate-300">
            {scrapeMsg}
          </div>
        )}
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      <footer className="border-t border-slate-800 text-center text-xs text-slate-600 py-4">
        Valencia Subastas — datos de onlineveilingmeester.nl
      </footer>
    </div>
  )
}
