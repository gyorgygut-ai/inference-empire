export type { NxTip } from './nx-tips';
export { NX_TIPS, getRandomNxTip, getNxTipsByCategory } from './nx-tips';

export {
  getNxTipToolDef,
  getNxTip,
  searchNxDocsToolDef,
  searchNxDocs,
  showNxCommandToolDef,
  serverTools,
} from './tools';

/**
 * Default Claude model id. Override at runtime with CHAT_MODEL.
 * Validated against ANTHROPIC_MODELS from @tanstack/ai-anthropic at build time
 * of this template (see README "How it works").
 */
export const DEFAULT_CHAT_MODEL = 'openrouter/free';

/** System prompt shared by the chat route. */
export const SYSTEM_PROMPT = `You are a friendly, concise assistant embedded in an Nx monorepo template that uses TanStack Start and TanStack AI.

You help developers learn Nx and TanStack. You have tools available:
- getNxTip: fetch a helpful Nx tip (optionally by category).
- searchNxDocs: search sample Nx docs for a keyword.
- showNxCommand: render a copy-ready Nx command card in the UI.

Guidelines:
- When the user asks for a tip, trick, or best practice, call getNxTip.
- When the user asks how to do something with Nx, call searchNxDocs first.
- When you want to suggest a concrete command to run, call showNxCommand so it renders as a nice card. Do not also paste the command in plain text.
- Keep answers short and practical. Use markdown.`;
