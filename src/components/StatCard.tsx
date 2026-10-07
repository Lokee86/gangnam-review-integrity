import type { ReactNode } from 'react'

export function StatCard({
  label,
  value,
  detail
}: {
  label: string
  value: ReactNode
  detail?: ReactNode
}) {
  return (
    <article className="stat-card">
      <div className="stat-card__label">{label}</div>
      <div className="stat-card__value">{value}</div>
      {detail ? <div className="stat-card__detail">{detail}</div> : null}
    </article>
  )
}
