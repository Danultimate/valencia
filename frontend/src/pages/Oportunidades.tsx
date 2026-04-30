import { useQuery } from '@tanstack/react-query'
import { Flame, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { fetchOpportunities } from '../api/client'
import OpportunityCard from '../components/OpportunityCard'
import StatCard from '../components/StatCard'

export default function Oportunidades() {
  const [minScore, setMinScore] = useState(0)
  const [limit, setLimit] = useState(24)

  const { data, isLoading, error } = useQuery({
    queryKey: ['opportunities', minScore, limit],
    queryFn: () => fetchOpportunities({ min_score: minScore || undefined, limit }),
    refetchInterval: 5 * 60 * 1000,
  })

  const topScore = data?.items[0]?.opportunity_score ?? null
  const avgScore =
    data && data.items.length > 0
      ? data.items.reduce((s, a) => s + (a.opportunity_score ?? 0), 0) / data.items.length
      : null

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-amber-500" />
          Oportunidades
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Subastas ordenadas por puntuación de oportunidad — mayor ahorro potencial primero.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard
          label="Total mostradas"
          value={data?.count ?? '—'}
          icon={<Flame className="w-5 h-5" />}
        />
        <StatCard
          label="Puntuación máxima"
          value={topScore !== null ? topScore.toFixed(1) : '—'}
          sub="en este listado"
        />
        <StatCard
          label="Puntuación media"
          value={avgScore !== null ? avgScore.toFixed(1) : '—'}
          sub="en este listado"
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400 whitespace-nowrap">Puntuación mínima</label>
          <input
            type="number"
            min={0}
            step={5}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="input w-24 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400 whitespace-nowrap">Límite</label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="input text-sm"
          >
            {[12, 24, 48, 96].map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card p-5 h-56 animate-pulse bg-slate-800" />
          ))}
        </div>
      )}

      {error && (
        <div className="card p-6 text-center text-red-400">
          Error al cargar oportunidades. Verifica que el servidor esté activo.
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="card p-12 text-center text-slate-500">
          No se encontraron oportunidades con los filtros actuales.
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((auction) => (
            <OpportunityCard key={auction.id} auction={auction} />
          ))}
        </div>
      )}
    </div>
  )
}
