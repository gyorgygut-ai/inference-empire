import type { Metadata } from "next"
import "./globals.css"
import { TooltipProvider } from "@/components/assistant-ui/elements/tooltip"

export const metadata: Metadata = {
  title: "Face Value",
  description: "AI face transformation",
}

export default function RootLayout({ children }: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  )
}
