import { toolDefinition } from '@tanstack/ai';
import { z } from 'zod';
import { NX_TIPS, getRandomNxTip, getNxTipsByCategory } from './nx-tips';

/**
 * Isomorphic tool definitions.
 *
 * A `toolDefinition()` describes the contract (name, description, typed
 * input/output schemas). You then attach a `.server()` implementation on the
 * server, and optionally a `.client()` implementation in the browser. The same
 * definition is shared by both sides, so the types stay in sync end to end.
 */

const nxCategory = z.enum([
  'caching',
  'tasks',
  'graph',
  'generators',
  'ci',
  'cloud',
]);

const nxTipOutput = z.object({
  id: z.number(),
  category: nxCategory,
  tip: z.string(),
  command: z.string().optional(),
});

/**
 * getNxTip - returns a random Nx tip (or one from a given category).
 * Pure server tool: the model calls it, the server runs it, the result is
 * fed back into the conversation.
 */
export const getNxTipToolDef = toolDefinition({
  name: 'getNxTip',
  description:
    'Get a helpful tip about using Nx. Optionally filter by category (caching, tasks, graph, generators, ci, cloud). Use this whenever the user asks for an Nx tip, trick, or best practice.',
  inputSchema: z.object({
    category: nxCategory
      .optional()
      .describe('Optional category to filter the tip by.'),
  }),
  outputSchema: nxTipOutput,
});

export const getNxTip = getNxTipToolDef.server((args, context) => {
  context?.emitCustomEvent('tool:progress', {
    tool: 'getNxTip',
    message: args.category
      ? `Looking up an Nx tip about ${args.category}`
      : 'Picking a random Nx tip',
  });

  if (args.category) {
    const matches = getNxTipsByCategory(args.category);
    if (matches.length > 0) {
      return matches[Math.floor(Math.random() * matches.length)];
    }
  }
  return getRandomNxTip();
});

/**
 * searchNxDocs - a stubbed docs search. In a real app this would hit a search
 * index or the Nx docs API; here it does a simple in-memory keyword match over
 * the tip catalog so the tool-calling flow is fully wired and demonstrable.
 */
export const searchNxDocsToolDef = toolDefinition({
  name: 'searchNxDocs',
  description:
    'Search the (sample) Nx documentation for a keyword and return matching tips. Use this when the user asks how to do something with Nx.',
  inputSchema: z.object({
    query: z.string().describe('The keyword or phrase to search for.'),
  }),
  outputSchema: z.object({
    query: z.string(),
    results: z.array(nxTipOutput),
    totalFound: z.number(),
  }),
});

export const searchNxDocs = searchNxDocsToolDef.server((args, context) => {
  context?.emitCustomEvent('tool:progress', {
    tool: 'searchNxDocs',
    message: `Searching Nx docs for "${args.query}"`,
  });

  const q = args.query.toLowerCase();
  const results = NX_TIPS.filter(
    (t) =>
      t.tip.toLowerCase().includes(q) ||
      t.category.toLowerCase().includes(q) ||
      (t.command?.toLowerCase().includes(q) ?? false),
  );

  return {
    query: args.query,
    results: [...results],
    totalFound: results.length,
  };
});

/**
 * showNxCommand - a "render-in-the-UI" tool. The server has no implementation;
 * instead the model emits a tool call and the client renders a rich command
 * card. This is the "define once -> AI tool + custom UI" pattern: the model
 * decides WHAT to show, the UI decides HOW. See apps/web for the client side.
 */
export const showNxCommandToolDef = toolDefinition({
  name: 'showNxCommand',
  description:
    'Display a runnable Nx command to the user in a copy-ready card. Use this whenever you want to suggest a concrete command the user should run.',
  inputSchema: z.object({
    command: z
      .string()
      .describe('The full Nx command, e.g. "nx affected -t build".'),
    explanation: z
      .string()
      .describe('A one-sentence explanation of what the command does.'),
  }),
  outputSchema: z.object({
    command: z.string(),
    explanation: z.string(),
  }),
});

/**
 * Every server-side tool the chat route should expose.
 * `showNxCommandToolDef` is intentionally definition-only here - its execution
 * happens on the client (see apps/web), which renders the command card.
 */
export const serverTools = [getNxTip, searchNxDocs, showNxCommandToolDef];
