/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { RealtimeClient } from "@openai/realtime-api-beta";
import { WavRecorder, WavStreamPlayer } from "./audio";
import {
  createVoiceSession,
  type RealtimeVoiceAdapter,
  type VoiceSessionControls,
  type VoiceSessionHelpers,
} from "@assistant-ui/react";
import { resolveTransport, type TransportConfig } from "./transport";

export interface OpenAIRealtimeVoiceAdapterOptions extends TransportConfig {
  instructions?: string;
  voice?: string;
  language?: string;
  onReady?: (client: unknown) => void;
  onMetadata?: (meta: {
    voices: { id: string; label: string }[];
    languages: { code: string; label: string }[];
    defaultVoice?: string;
    defaultLanguage?: string;
  }) => void;
}

/**
 * assistant-ui RealtimeVoiceAdapter backed by the OpenAI Realtime protocol that
 * our realtime relay worker speaks. Reuses the proven RealtimeClient + wavtools
 * plumbing from the OpenAI Realtime Console and maps its events onto
 * assistant-ui's voice session helpers.
 */
export class OpenAIRealtimeVoiceAdapter implements RealtimeVoiceAdapter {
  constructor(private readonly opts: OpenAIRealtimeVoiceAdapterOptions = {}) {}

  connect(options: { abortSignal?: AbortSignal }): RealtimeVoiceAdapter.Session {
    return createVoiceSession(options, async (helpers: VoiceSessionHelpers) => {
      const transport = resolveTransport(this.opts);

      const client = new RealtimeClient(
        transport.apiKey
          ? {
              url: transport.url,
              apiKey: transport.apiKey,
              dangerouslyAllowAPIKeyInBrowser: true,
            }
          : { url: transport.url }
      );

      const wavRecorder = new WavRecorder({ sampleRate: 24000 });
      const wavStreamPlayer = new WavStreamPlayer({ sampleRate: 24000 });

      const emitVolumeFromMic = (mono: Int16Array) => {
        let sum = 0;
        for (let i = 0; i < mono.length; i++) {
          const s = mono[i] / 32768;
          sum += s * s;
        }
        const rms = Math.sqrt(sum / Math.max(1, mono.length));
        helpers.emitVolume(Math.min(1, rms * 4));
      };

      client.on("conversation.updated", async ({ item, delta }: any) => {
        if (delta?.audio) {
          wavStreamPlayer.add16BitPCM(delta.audio, item.id);
        }
        if (item.role === "user" && item.formatted?.transcript) {
          helpers.emitTranscript({
            role: "user",
            text: item.formatted.transcript,
            isFinal: item.status === "completed",
          });
        }
        if (item.role === "assistant") {
          const text = item.formatted?.text ?? item.formatted?.transcript ?? "";
          if (text) {
            helpers.emitTranscript({
              role: "assistant",
              text,
              isFinal: item.status === "completed",
            });
          }
        }
        if (item.role === "assistant" && item.status !== "completed") {
          helpers.emitMode("speaking");
        } else if (item.role === "user") {
          helpers.emitMode("listening");
        }
      });

      client.on("conversation.interrupted", () => {
        wavStreamPlayer.interrupt();
        helpers.emitMode("listening");
      });

      client.on("error", (event: any) => {
        console.error("[OpenAIRealtimeVoiceAdapter] error", event);
        helpers.end("error", event);
      });

      // Endpoint advertises its capabilities (our worker only). Drives the
      // voice/language picker; hidden for plain OpenAI endpoints.
      // NOTE: the realtime-api-beta SDK dispatches server events as
      // `server.{type}` (see api.js receive()), so the event is
      // `server.session.created`, not `session.created`.
      client.on("server.session.created", (event: any) => {
        const s = event?.session ?? (client as any).session;
        if (s?.available_voices) {
          this.opts.onMetadata?.({
            voices: s.available_voices,
            languages: s.available_languages ?? [],
            defaultVoice: s.voice,
            defaultLanguage: s.language,
          });
        }
      });

      await wavRecorder.begin();
      await wavStreamPlayer.connect();
      await client.connect();
      helpers.setStatus({ type: "running" });
      helpers.emitMode("listening");

      this.opts.onReady?.(client);

      client.updateSession({
        instructions:
          this.opts.instructions ??
          "You are a helpful, concise voice assistant. Respond naturally and briefly.",
      });
      client.updateSession({ input_audio_transcription: { model: "whisper-1" } });

      // Always send turn_detection (protocol-correct for our worker, which
      // performs its own VAD internally and ignores this field). Also send
      // voice/language when provided. realtime.send takes (eventName, data).
      client.realtime.send("session.update", {
        ...(this.opts.voice ? { voice: this.opts.voice } : {}),
        ...(this.opts.language ? { language: this.opts.language } : {}),
        turn_detection: { type: "server_vad" },
      });

      const micLoop = (data: { mono: Int16Array }) => {
        client.appendInputAudio(data.mono);
        emitVolumeFromMic(data.mono);
      };

      // Our worker does its own VAD, so we must always stream mic audio —
      // never gate capture on the SDK's session config (getTurnDetectionType
      // stays null because the SDK never merges the server's session.created).
      await wavRecorder.record(micLoop);

      const controls: VoiceSessionControls = {
        disconnect: () => {
          try {
            client.disconnect();
          } catch {
            /* noop */
          }
          wavRecorder.end().catch(() => {});
          wavStreamPlayer.interrupt();
          helpers.end("finished");
        },
        mute: () => {
          wavRecorder.pause().catch(() => {});
        },
        unmute: () => {
          wavRecorder.record(micLoop).catch(() => {});
        },
      };

      return controls;
    });
  }
}
