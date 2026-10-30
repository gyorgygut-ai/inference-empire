import React, { type ReactNode } from "react"

export type ToggleOption = {
  value: string
  label: ReactNode
}

export const Toggle = ({
  label,
  options,
  value,
  onValueChange,
}: {
  label: string
  options: readonly ToggleOption[]
  value: string
  onValueChange: (value: string) => void
}) => (
  <div
    aria-label={label}
    className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/50 p-1 shadow-sm"
    role="group"
  >
    {options.map((option) => (
      <button
        aria-pressed={option.value === value}
        className={`rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${option.value === value ? "bg-background text-foreground shadow" : "text-muted-foreground hover:text-foreground"}`}
        key={option.value}
        onClick={() => onValueChange(option.value)}
        type="button"
      >
        {option.label}
      </button>
    ))}
  </div>
)
