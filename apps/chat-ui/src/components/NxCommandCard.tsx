import { useState } from 'react';
import { Check, Copy, Terminal } from 'lucide-react';

/**
 * Renders the output of the `showNxCommand` tool: a copy-ready command card.
 * The model decides WHAT command to surface; this component decides HOW it
 * looks. This is the "define the tool once, render it richly" pattern.
 */
export function NxCommandCard({
  command,
  explanation,
}: {
  command: string;
  explanation: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard?.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-emerald-500/30 bg-zinc-900/80">
      <div className="flex items-center justify-between border-b border-emerald-500/20 bg-emerald-500/10 px-4 py-2">
        <div className="flex items-center gap-2 text-emerald-300">
          <Terminal className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-wide">
            Nx command
          </span>
        </div>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-emerald-300 transition-colors hover:bg-emerald-500/20"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy
            </>
          )}
        </button>
      </div>
      <pre className="overflow-x-auto px-4 py-3 font-mono text-sm text-emerald-200">
        <code>{command}</code>
      </pre>
      {explanation && (
        <p className="border-t border-zinc-800 px-4 py-2 text-sm text-zinc-400">
          {explanation}
        </p>
      )}
    </div>
  );
}
