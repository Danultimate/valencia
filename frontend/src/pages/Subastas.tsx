import { useQuery } from '@tanstack/react-query'
import { formatDistanceToNowStrict } from 'date-fns'
import { es } from 'date-fns/locale'
import { ChevronLeft, ChevronRight, ExternalLink, Gavel } from 'lucide-react'
import { useState } from 'react'
import { fetchAuctions } from '../api/client'
import ScoreBadge from '../components/ScoreBadge'
import StatCard from '../components/StatCard'

const PAGE_SIZE = 25

function eur(v: number | null) {
  if (v === null) return '—'
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(v)
}

function relTime(iso: string | null) {
  if (!iso) return '—'
  try {
    return formatDistanceToNowStrict(new Date(iso), { locale: es, addSuffix: true })
  } catch {
    return '—'
  }
}

export default function Subastas() {
  const [page, setPage] = useState(0)
  const [category, setCategory] = useState('')
  const [activeOnly, setActiveOnly] = useState(true)

  const { data, isLoading, error } = useQuery({
    queryKey: ['auctions', page, category, activeOnly],
    queryFn: () =>
      fetchAuctions({
        category: category || undefined,
        active_only: activeOnly,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    placeholderData: (prev) => prev,
    refetchInterval: 5 * 60 * 1000,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  function handleCategoryChange(val: string) {
    setCategory(val)
    setPage(0)
  }

  function handleActiveOnlyChange(val: boolean) {
    setActiveOnly(val)
    setPage(0)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <Gavel className="w-6 h-6 text-amber-500" />
          Subastas
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Listado completo de subastas recuperadas del sitio de origen.
        </p>
      </div>

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-2 gap-4">
          <StatCard label="Total resultados" value={data.total} />
          <StatCard label="Esta página" value={data.items.length} sub={`página ${page + 1} de ${totalPages || 1}`} />
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Filtrar por categoría…"
          value={category}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="input text-sm w-52"
        />
        <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => handleActiveOnlyChange(e.target.checked)}
            className="w-4 h-4 rounded bg-slate-700 border-slate-600 accent-amber-500"
          />
          Solo activas
        </label>
      </div>

      {/* Error */}
      {error && (
        <div className="card p-6 text-center text-red-400">
          Error al cargar subastas. Verifica que el servidor esté activo.
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left">
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium">Título</th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium">Categoría</th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium text-right">Tasación</th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium text-right">Puja actual</th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium">Cierre</th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium text-center">Score</th>
                <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wide font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {isLoading &&
                Array.from({ length: PAGE_SIZE }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-slate-700 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))}

              {!isLoading && data?.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                    No se encontraron subastas con los filtros actuales.
                  </td>
                </tr>
              )}

              {data?.items.map((auction) => (
                <tr key={auction.id} className="table-row-hover">
                  <td className="px-4 py-3 max-w-xs">
                    <span className="line-clamp-2 text-slate-200 leading-snug">{auction.title}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                    {auction.category ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300 tabular-nums whitespace-nowrap">
                    {eur(auction.appraisal_value)}
                  </td>
                  <td className="px-4 py-3 text-right text-amber-400 tabular-nums font-medium whitespace-nowrap">
                    {eur(auction.current_bid)}
                  </td>
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                    {relTime(auction.end_date)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <ScoreBadge score={auction.opportunity_score} size="sm" />
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={auction.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-amber-400 transition-colors"
                      title="Ver en origen"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="border-t border-slate-700 px-4 py-3 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Página {page + 1} de {totalPages}
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-ghost p-1.5 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="btn-ghost p-1.5 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
