import React from "react"
import HeroImage from "./HeroImage"

export const SplitLayout = ({ chat }: { chat: React.ReactNode }) => (
  <div className="min-h-screen bg-background">
    <aside className="hidden md:fixed md:inset-y-0 md:left-0 md:flex md:overflow-hidden bg-sidebar md:w-1/2 lg:w-2/3">
      <HeroImage />
    </aside>
    <main className="min-h-screen min-w-0 px-4 py-6 md:ml-[50%] lg:ml-[66.666667%] md:w-1/2 lg:w-1/3">
      {chat}
    </main>
  </div>
)

export default SplitLayout
