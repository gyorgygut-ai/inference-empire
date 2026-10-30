import React from "react"
export const CenteredLayout = ({ chat }: { chat: React.ReactNode }) => (
  <main className="min-h-screen bg-background flex">
    <div className="flex-1 min-w-0 px-4 py-6">{chat}</div>
  </main>
)

export default CenteredLayout
