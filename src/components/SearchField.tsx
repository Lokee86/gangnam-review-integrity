interface SearchFieldProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function SearchField({ value, onChange, placeholder = 'Search' }: SearchFieldProps) {
  return (
    <label className="search-field">
      <span aria-hidden="true">⌕</span>
      <input
        aria-label={placeholder}
        onChange={event => onChange(event.target.value)}
        placeholder={placeholder}
        type="search"
        value={value}
      />
      {value ? (
        <button aria-label="Clear search" onClick={() => onChange('')} type="button">
          ×
        </button>
      ) : null}
    </label>
  )
}
