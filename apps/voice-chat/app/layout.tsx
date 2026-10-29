import React from "react"
import { vocabulary } from "@/messages"
import "./globals.css"

export const metadata = {
  title: vocabulary.meta.name,
  description: vocabulary.meta.description,
  manifest: "/site.webmanifest",
}

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
}

const RootLayout = ({ children }: Readonly<{ children: React.ReactNode }>) => (
  <html lang="en" className="h-full">
    <body className="h-full">{children}</body>
  </html>
)

export default RootLayout
