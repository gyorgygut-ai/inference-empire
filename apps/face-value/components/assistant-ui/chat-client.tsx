"use client";

import { RuntimeProvider } from "./runtime-provider";
import type { PublicOutcome } from "@/outcomes";
import { RootAssistantUiComponent } from "./root-assistant-ui-component";

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => (
  <RuntimeProvider
    suggestions={outcomes}
    childrenFn={() => <RootAssistantUiComponent outcomes={outcomes} />}
  />
);
