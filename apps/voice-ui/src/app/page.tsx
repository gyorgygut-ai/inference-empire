import { VoiceChat } from "@/voice-ui";

export default function Home() {
  return (
    <main className="h-screen w-screen">
      <VoiceChat strategy="proxy" />
    </main>
  );
}
