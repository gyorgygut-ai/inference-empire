import React from "react";
import { ChatClient } from "@/components/chat/chat-client";

export const dynamic = "force-dynamic";

const Home = async () => (
  <main className="min-h-screen bg-background flex">
    <aside className="hidden md:flex md:w-2/3 bg-sidebar border-r border-border" />
    <div className="flex-1 md:w-1/3 min-w-0 px-4 py-6">
      <ChatClient />
    </div>
  </main>
);

export default Home;
