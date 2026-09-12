import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Face Value",
  description: "AI face transformation",
}

export default function RootLayout({ children }: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
