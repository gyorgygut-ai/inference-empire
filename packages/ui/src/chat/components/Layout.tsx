"use client"
import React from "react"

export const Layout = ({ Messages, Interrupts, Queue }: {
  Messages: React.ComponentType;
  Interrupts: React.ComponentType;
  Queue: React.ComponentType;
}) => (
  <div className="h-full flex flex-col">
    <Messages />
    <Interrupts />
    <Queue />
  </div>
)