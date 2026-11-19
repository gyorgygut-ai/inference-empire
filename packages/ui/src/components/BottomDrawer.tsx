import React from "react"
import type { ReactNode } from "react"

export const BottomDrawer = ({
  children,
  label,
  open,
}: {
  children: ReactNode
  label: string
  open: boolean
}) => {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <div aria-hidden="true" className="absolute inset-0 bg-black/50" />
      <section
        aria-label={label}
        aria-modal="true"
        className="relative max-h-[85vh] w-full overflow-y-auto rounded-t-2xl bg-background p-4 shadow-xl"
        role="dialog"
      >
        {children}
      </section>
    </div>
  )
}
