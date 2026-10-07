export function ConfidenceBar({ value }: { value: number }) {
  const bounded = Math.max(0, Math.min(1, value))
  return (
    <div className="confidence" aria-label={`${Math.round(bounded * 100)}% confidence`}>
      <div className="confidence__track">
        <div className="confidence__fill" style={{ width: `${bounded * 100}%` }} />
      </div>
      <span>{Math.round(bounded * 100)}%</span>
    </div>
  )
}
