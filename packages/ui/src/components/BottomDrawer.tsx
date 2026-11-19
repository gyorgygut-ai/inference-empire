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
}) => (
  <div
    aria-hidden={!open}
    className={`-mb-6 w-full shrink-0 ${open ? "mt-auto" : ""}`}
  >
    <div
      aria-hidden="true"
      className={`absolute -inset-x-4 -inset-y-6 z-40 bg-black/50 transition-opacity duration-300 ease-out motion-reduce:transition-none ${
        open ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
    />
    <div
      className={`grid w-full transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none ${
        open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
      }`}
    >
      <div className="min-h-0 overflow-hidden">
        <section
          aria-label={label}
          aria-modal={open}
          className={`relative z-50 max-h-[85dvh] w-full overflow-y-auto rounded-t-2xl bg-background p-4 shadow-xl transition-transform duration-300 ease-out motion-reduce:transition-none ${
            open ? "translate-y-0" : "translate-y-full"
          }`}
          inert={!open}
          role="dialog"
        >
          {children}
        </section>
      </div>
    </div>
  </div>
)
