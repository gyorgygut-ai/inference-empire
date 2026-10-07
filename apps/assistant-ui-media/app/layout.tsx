import type { Metadata } from "next";
import React from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Image Generation Example",
  description: "Example using @assistant-ui/react image generation primitives",
};

const RootLayout = ({
  children,
}: Readonly<{ children: React.ReactNode }>) => (
  <html lang="en">
    <body className="bg-background text-foreground h-dvh">{children}</body>
  </html>
);

export default RootLayout;