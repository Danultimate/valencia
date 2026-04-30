interface Props {
  score: number | null
  size?: 'sm' | 'md'
}

export default function ScoreBadge({ score, size = 'md' }: Props) {
  if (score === null) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-400">
        —
      </span>
    )
  }

  const color =
    score >= 50
      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
      : score >= 10
        ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
        : 'bg-slate-700 text-slate-400 border-slate-600'

  const padding = size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'

  return (
    <span className={`inline-flex items-center rounded border font-semibold tabular-nums ${padding} ${color}`}>
      {score.toFixed(1)}
    </span>
  )
}
