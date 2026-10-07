export interface Segment<T extends string> {
  id: T
  label: string
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange
}: {
  options: readonly Segment<T>[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="segmented-control" role="group">
      {options.map(option => (
        <button
          aria-pressed={option.id === value}
          className={option.id === value ? 'is-active' : undefined}
          key={option.id}
          onClick={() => onChange(option.id)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
