"use client";

import { useEffect } from "react";
import { useAppChat } from "./chat-hook";

export const ChatClient = () => {
  const chat = useAppChat();

  // Seed initial message once
  useEffect(() => {
    chat.append({
      role: "assistant",
      content: "Select an outcome.",
    });
  }, []);

  return <chat.AppChat />;
};
