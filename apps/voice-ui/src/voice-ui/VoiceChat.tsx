/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable react-hooks/refs */
"use client";

import { useRef, useState } from "react";
import { Thread } from "@/components/assistant-ui/thread";
import { VoiceControl } from "@/components/assistant-ui/voice";
import {
  AuiIf,
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";
import {
  OpenAIRealtimeVoiceAdapter,
  type OpenAIRealtimeVoiceAdapterOptions,
} from "./OpenAIRealtimeVoiceAdapter";

const stubChatModel: ChatModelAdapter = {
  async *run() {
    yield { content: [{ type: "text", text: "" }] };
  },
};

type Meta = {
  voices: { id: string; label: string }[];
  languages: { code: string; label: string }[];
};

// Fallback so the picker always renders even before (or without) the worker's
// session.created metadata. Overwritten once metadata arrives.
const DEFAULT_META: Meta = {
  voices: [
    { id: "GutAI", label: "GutAI" },
    { id: "ff", label: "ff" },
    { id: "bp", label: "bp" },
    { id: "bo", label: "bo" },
    { id: "sa", label: "sa" },
  ],
  languages: [
    { code: "en", label: "English" },
    { code: "hu", label: "Hungarian" },
  ],
};

export function VoiceChat(
  props: OpenAIRealtimeVoiceAdapterOptions & { className?: string }
) {
  // Phase 2: voice/language lists come from the endpoint (the worker
  // advertises them in session.created). Start with a sensible default so the
  // picker is never blank, then update from the worker's metadata.
  const [meta, setMeta] = useState<Meta>(DEFAULT_META);
  const [voice, setVoice] = useState("GutAI");
  const [language, setLanguage] = useState("en");
  const clientRef = useRef<any>(null);

  const runtime = useLocalRuntime(stubChatModel, {
    adapters: {
      voice: new OpenAIRealtimeVoiceAdapter({
        strategy: props.strategy,
        workerUrl: props.workerUrl,
        token: props.token,
        instructions: props.instructions,
        voice,
        language,
        onReady: (c: unknown) => {
          clientRef.current = c;
        },
        onMetadata: (m) => {
          setMeta({ voices: m.voices, languages: m.languages });
          setVoice(m.defaultVoice ?? "GutAI");
          setLanguage(m.defaultLanguage ?? "en");
        },
      }),
    },
  });

  const pushSession = (v: string, l: string) => {
    console.log("[VoiceChat] pushSession", { voice: v, language: l });
    clientRef.current?.realtime.send("session.update", {
      session: { voice: v, language: l },
    });
  };

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className={`flex h-full flex-col ${props.className ?? ""}`}>
        <AuiIf condition={(s) => s.thread.capabilities.voice}>
          <VoiceControl />
        </AuiIf>
        {meta && (
          <div className="flex gap-2 p-2">
            <select
              value={voice}
              onChange={(e) => {
                const v = e.target.value;
                setVoice(v);
                pushSession(v, language);
              }}
            >
              {meta.voices.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
            <select
              value={language}
              onChange={(e) => {
                const l = e.target.value;
                setLanguage(l);
                pushSession(voice, l);
              }}
            >
              {meta.languages.map((x) => (
                <option key={x.code} value={x.code}>
                  {x.label}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="min-h-0 flex-1">
          <Thread />
        </div>
      </div>
    </AssistantRuntimeProvider>
  );
}

export default VoiceChat;
