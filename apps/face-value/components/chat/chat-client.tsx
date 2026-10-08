"use client";

import React from "react";
import { useAppChat } from "./chat-hook";
import { OutcomesProvider } from "./outcomes-context";
import type { PublicOutcome } from "@/outcomes/outcomes";

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat();
  return (
    <OutcomesProvider outcomes={outcomes}>
      <chat.AppChat />
    </OutcomesProvider>
  );
};
