import type { Metadata } from "next"
import React from "react";
import "./globals.css"

export const metadata: Metadata = {
  title: "Face Value",
  description: "AI face transformation",
}

const RootLayout = ({ children }: Readonly<{ children: React.ReactNode }>) => (
  <html lang="en" className="h-full">
    <body className="h-full">{children}</body>
  </html>
);

export default RootLayout;