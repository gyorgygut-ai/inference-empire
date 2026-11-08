import React, { type ReactNode } from "react"

export type ToggleOption = {
  value: string
  label: ReactNode
}

type ToggleProps<TOptions extends readonly ToggleOption[]> = {
  label: string
  options: TOptions
  value: TOptions[number]["value"]
  onValueChange: (value: TOptions[number]["value"]) => void
}

export const Toggle = <const TOptions extends readonly ToggleOption[],>({
  label,
  options,
  value,
  onValueChange,
}: ToggleProps<TOptions>) => (
  <div
    aria-label={label}
    className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/50 p-1 shadow-sm"
    role="group"
  >
    {options.map((option) => (
      <button
        aria-pressed={option.value === value}
        className={`rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${option.value === value ? "bg-background text-foreground shadow" : "text-foreground hover:bg-background/60"}`}
        key={option.value}
        onClick={() => onValueChange(option.value)}
        type="button"
      >
        {option.label}
      </button>
    ))}
  </div>
)
