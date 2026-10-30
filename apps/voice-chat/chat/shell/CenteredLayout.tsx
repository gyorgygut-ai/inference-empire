import React from "react"
export const CenteredLayout = ({ chat }: { chat: React.ReactNode }) => (
  <main className="relative min-h-svh bg-background">{chat}</main>
)

export default CenteredLayout
