import { useEffect, useRef, useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { Send, Sparkles, Square, Wrench } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import { fetchServerSentEvents, useChat } from '@tanstack/ai-react';
import { clientTools } from '@tanstack/ai-client';
import type { UIMessage } from '@tanstack/ai-react';
import { showNxCommandToolDef } from '@inference-empire/ai';
import { NxCommandCard } from '../components/NxCommandCard';

// The showNxCommand tool has no server execution: the model emits a tool call
// and the browser "executes" it by simply echoing the args, which we then
// render as a rich command card. One definition, shared types, custom UI.
const showNxCommandClient = showNxCommandToolDef.client((args) => args);

const tools = clientTools(showNxCommandClient);

const SUGGESTIONS = [
  'Give me a random Nx tip',
  'How do I run only affected projects?',
  'What does remote caching do?',
  'Show me the command to visualize the project graph',
];

function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-xl space-y-8 text-center">
        <div className="space-y-3">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-linear-to-br from-violet-500 to-indigo-600 shadow-lg shadow-indigo-500/30">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Nx + TanStack AI
          </h1>
          <p className="mx-auto max-w-md text-sm text-zinc-400">
            A streaming, type-safe AI chat with tool calling - built on TanStack
            Start and TanStack AI, in an Nx monorepo. Ask about Nx and watch the
            model call real tools.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-3 text-left text-sm text-zinc-300 transition-colors hover:border-violet-500/40 hover:bg-zinc-900"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ToolProgress({ message }: { message: string }) {
  return (
    <div className="mt-2 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300">
      <Wrench className="h-3.5 w-3.5 animate-pulse" />
      {message}
    </div>
  );
}

function MessagePart({ part }: { part: UIMessage['parts'][number] }) {
  if (part.type === 'text' && part.content) {
    return (
      <div className="prose prose-sm prose-invert max-w-none prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800">
        <ReactMarkdown
          rehypePlugins={[rehypeSanitize, rehypeHighlight]}
          remarkPlugins={[remarkGfm]}
        >
          {part.content}
        </ReactMarkdown>
      </div>
    );
  }

  // showNxCommand tool result -> render the command card
  if (
    part.type === 'tool-call' &&
    part.name === 'showNxCommand' &&
    part.output
  ) {
    const output = part.output as { command: string; explanation: string };
    return (
      <NxCommandCard
        command={output.command}
        explanation={output.explanation}
      />
    );
  }

  return null;
}

function Messages({ messages }: { messages: Array<UIMessage> }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-2xl space-y-4">
        {messages.map((message) => (
          <div key={message.id} className="flex items-start gap-3">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-semibold text-white ${
                message.role === 'assistant'
                  ? 'bg-linear-to-br from-violet-500 to-indigo-600'
                  : 'bg-zinc-700'
              }`}
            >
              {message.role === 'assistant' ? 'AI' : 'You'}
            </div>
            <div className="min-w-0 flex-1 pt-1 text-sm text-zinc-100">
              {message.parts.map((part, i) => (
                <MessagePart key={i} part={part} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ChatPage() {
  const [input, setInput] = useState('');
  const [toolMessage, setToolMessage] = useState<string | null>(null);

  const { messages, sendMessage, isLoading, error, stop } = useChat({
    connection: fetchServerSentEvents('/api/chat'),
    tools,
    onCustomEvent: (eventType, data) => {
      if (eventType === 'tool:progress') {
        const value = data as { message?: string } | undefined;
        if (value?.message) {
          setToolMessage(value.message);
          setTimeout(() => setToolMessage(null), 2500);
        }
      }
    },
  });

  const submit = (text: string) => {
    const value = text.trim();
    if (!value || isLoading) return;
    sendMessage(value);
    setInput('');
  };

  return (
    <div className="flex h-screen flex-col bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950/80 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-violet-400" />
          <span className="text-sm font-semibold tracking-tight text-white">
            Nx + TanStack AI
          </span>
        </div>
        <a
          href="https://cloud.nx.app/get-started"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-violet-500"
        >
          Connect to Nx Cloud
        </a>
      </header>

      {messages.length === 0 ? (
        <EmptyState onPick={submit} />
      ) : (
        <Messages messages={messages} />
      )}

      {toolMessage && (
        <div className="mx-auto mb-3 w-full max-w-2xl px-4">
          <ToolProgress message={toolMessage} />
        </div>
      )}

      {error && (
        <div className="mx-auto mt-2 w-full max-w-2xl px-4">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            {error.message}
          </div>
        </div>
      )}

      <div className="border-t border-zinc-800 bg-zinc-950/80 px-4 py-4 backdrop-blur">
        <div className="mx-auto max-w-2xl">
          {isLoading && (
            <div className="mb-3 flex justify-center">
              <button
                onClick={stop}
                className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
                Stop
              </button>
            </div>
          )}
          <div className="relative flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  submit(input);
                }
              }}
              placeholder="Ask about Nx, TanStack, caching, the project graph..."
              rows={1}
              disabled={isLoading}
              className="w-full resize-none rounded-xl border border-zinc-800 bg-zinc-900 py-3 pl-4 pr-12 text-sm text-white placeholder-zinc-500 shadow-lg focus:border-violet-500/50 focus:outline-none focus:ring-2 focus:ring-violet-500/30 disabled:opacity-50"
            />
            <button
              onClick={() => submit(input)}
              disabled={!input.trim() || isLoading}
              className="absolute inset-y-2 right-2 flex aspect-square items-center justify-center rounded-lg bg-violet-600 text-white transition-colors hover:bg-violet-500 disabled:bg-zinc-700 disabled:text-zinc-500"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-zinc-600">
            Powered by TanStack AI - set ANTHROPIC_API_KEY to chat with Claude
          </p>
        </div>
      </div>
    </div>
  );
}

export const Route = createFileRoute('/')({
  component: ChatPage,
});
