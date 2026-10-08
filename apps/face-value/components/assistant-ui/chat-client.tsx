"use client";

import React from "react";
import { ChatProvider } from "@/components/tanstack-chat/ChatProvider";
import { MessageList } from "@/components/tanstack-chat/MessageList";
import { AttachmentComposer } from "@/components/tanstack-chat/AttachmentComposer";
import type { PublicOutcome } from "@/outcomes";

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => (
  <ChatProvider initialOutcomes={outcomes}>
    <div className="h-full flex flex-col">
      <MessageList />
      <AttachmentComposer />
    </div>
  </ChatProvider>
);