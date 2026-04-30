import type { ReactNode } from 'react'

interface Props {
  label: string
  value: ReactNode
  sub?: string
  icon?: ReactNode
}

export default function StatCard({ label, value, sub, icon }: Props) {
  return (
    <div className="card p-4 flex items-start gap-4">
      {icon && (
        <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400 shrink-0">
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-slate-400 uppercase tracking-wide truncate">{label}</p>
        <p className="text-2xl font-bold text-slate-100 mt-0.5 truncate">{value}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  )
}
