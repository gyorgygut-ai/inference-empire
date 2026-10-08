import type { Metadata } from "next"
import React from "react"
import "./globals.css"

export const metadata: Metadata = {
  title: "Face Value",
  description: "AI face transformation",
  icons: {
    icon: [
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
    other: [{ url: "/site.webmanifest", type: "application/manifest+json" }],
  },
}

const RootLayout = ({ children }: Readonly<{ children: React.ReactNode }>) => (
  <html lang="en" className="h-full">
    <body className="h-full">{children}</body>
  </html>
)

export default RootLayout
