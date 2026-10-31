"use client"
import React from "react"

export const Layout = ({ Messages, Interrupts, Queue }: {
  Messages: React.ComponentType;
  Interrupts: React.ComponentType;
  Queue: React.ComponentType;
}) => (
  <div className="flex flex-col gap-6">
    <Messages />
    <Interrupts />
    <Queue />
  </div>
)
