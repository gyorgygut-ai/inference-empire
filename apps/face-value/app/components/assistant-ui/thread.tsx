"use client"
import { useChat } from "./chat-context"
import {
  ThreadPrimitive,
  MessagePrimitive,
  SuggestionPrimitive,
  AuiIf,
} from "@assistant-ui/react"
import Composer from "./composer"

type ThreadProps = {
  outcomes: { id: string; title: string }[]
  serverOnline: boolean
}

export default function Thread({ outcomes, serverOnline }: ThreadProps) {
  const { setSelectedOutcomeId } = useChat()

  return (
    <ThreadPrimitive.Root className="flex flex-col h-full">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
        <AuiIf condition={(s) => s.thread.isEmpty}>
          <ThreadPrimitive.Suggestions className="p-4 space-y-2">
            {() =>
              outcomes.map((outcome) => (
                <SuggestionPrimitive.Trigger
                  key={outcome.id}
                  send={{ text: outcome.id }}
                  onClick={() => setSelectedOutcomeId(outcome.id)}
                  className="w-full text-left px-3 py-2 rounded border border-gray-200 hover:bg-gray-50"
                >
                  <SuggestionPrimitive.Title>
                    {outcome.title}
                  </SuggestionPrimitive.Title>
                </SuggestionPrimitive.Trigger>
              ))
            }
          </ThreadPrimitive.Suggestions>
        </AuiIf>

        <ThreadPrimitive.Messages>
          {({ message }) => (
            <MessagePrimitive.Root key={message.id}>
              <MessagePrimitive.Content
                components={{
                  Text: ({ text }) => <p>{text}</p>,
                  Image: ({ image }) => (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={image} alt="Generated" className="max-w-full rounded" />
                  ),
                }}
              />
            </MessagePrimitive.Root>
          )}
        </ThreadPrimitive.Messages>
      </ThreadPrimitive.Viewport>

      <ThreadPrimitive.ViewportFooter className="sticky bottom-0 border-t bg-white">
        <Composer serverOnline={serverOnline} />
      </ThreadPrimitive.ViewportFooter>
    </ThreadPrimitive.Root>
  )
}
