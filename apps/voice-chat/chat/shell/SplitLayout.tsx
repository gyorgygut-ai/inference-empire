import React from "react"
import HeroImage from "./HeroImage"

export const SplitLayout = ({ chat }: { chat: React.ReactNode }) => (
  <main className="min-h-screen bg-background flex">
    <aside className="hidden md:flex md:w-2/3 bg-sidebar border-r border-border">
      <HeroImage />
    </aside>
    <div className="flex-1 md:w-1/3 min-w-0 px-4 py-6">{chat}</div>
  </main>
)

export default SplitLayout
