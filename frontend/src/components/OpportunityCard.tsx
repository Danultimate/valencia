import { formatDistanceToNowStrict } from 'date-fns'
import { es } from 'date-fns/locale'
import { Clock, ExternalLink, MapPin, Tag } from 'lucide-react'
import type { Auction } from '../types'
import ScoreBadge from './ScoreBadge'

interface Props {
  auction: Auction
}

function formatEur(value: number | null) {
  if (value === null) return '—'
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value)
}

export default function OpportunityCard({ auction }: Props) {
  const endDate = auction.end_date ? new Date(auction.end_date) : null
  const timeLeft = endDate
    ? formatDistanceToNowStrict(endDate, { locale: es, addSuffix: true })
    : null

  const saving =
    auction.appraisal_value && auction.current_bid
      ? auction.appraisal_value - auction.current_bid
      : null

  const savingPct =
    saving && auction.appraisal_value
      ? Math.round((saving / auction.appraisal_value) * 100)
      : null

  return (
    <div className="card p-5 flex flex-col gap-4 hover:border-slate-500 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-slate-100 font-medium leading-snug line-clamp-2 flex-1">
          {auction.title}
        </h3>
        <ScoreBadge score={auction.opportunity_score} />
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-400">
        {auction.category && (
          <span className="flex items-center gap-1">
            <Tag className="w-3 h-3" />
            {auction.category}
          </span>
        )}
        {auction.location && (
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {auction.location}
          </span>
        )}
        {timeLeft && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {timeLeft}
          </span>
        )}
      </div>

      {/* Price grid */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="bg-slate-900/60 rounded-lg p-2">
          <p className="text-xs text-slate-500 mb-0.5">Tasación</p>
          <p className="text-sm font-semibold text-slate-200">{formatEur(auction.appraisal_value)}</p>
        </div>
        <div className="bg-slate-900/60 rounded-lg p-2">
          <p className="text-xs text-slate-500 mb-0.5">Puja actual</p>
          <p className="text-sm font-semibold text-amber-400">{formatEur(auction.current_bid)}</p>
        </div>
        <div className="bg-slate-900/60 rounded-lg p-2">
          <p className="text-xs text-slate-500 mb-0.5">Ahorro</p>
          <p className={`text-sm font-semibold ${saving && saving > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
            {savingPct !== null ? `${savingPct}%` : '—'}
          </p>
        </div>
      </div>

      {/* CTA */}
      <a
        href={auction.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-1.5 text-sm text-amber-500 hover:text-amber-400 border border-amber-500/30 hover:border-amber-400/50 rounded-lg py-2 transition-colors"
      >
        Ver subasta
        <ExternalLink className="w-3.5 h-3.5" />
      </a>
    </div>
  )
}
