import { createFileRoute } from '@tanstack/react-router'
import {
  chat,
  chatParamsFromRequestBody,
  createChatOptions,
  maxIterations,
  mergeAgentTools,
  toServerSentEventsResponse,
} from '@tanstack/ai'
import { openRouterText } from '@tanstack/ai-openrouter'
// To switch providers, swap the adapter above and below for one of:
//   import { openaiText } from '@tanstack/ai-openai'   -> openaiText(model)
//   import { geminiText } from '@tanstack/ai-gemini'   -> geminiText(model)
//   import { openRouterText } from '@tanstack/ai-openrouter' -> openRouterText(model)
// The rest of the route (tools, SSE, useChat) is provider-agnostic.
import {
  serverTools,
  SYSTEM_PROMPT,
  DEFAULT_CHAT_MODEL,
} from '@inference-empire/ai'

// Read the model from the environment so it is configurable per deployment.
// Defaults to openrouter/free via KILO_API_KEY.
const MODEL = process.env.CHAT_MODEL || DEFAULT_CHAT_MODEL

export const Route = createFileRoute('/api/chat')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        if (!process.env.KILO_API_KEY) {
          return new Response(
            JSON.stringify({
              error:
                'KILO_API_KEY is not set. Add it to your environment to use OpenRouter.',
            }),
            { status: 500, headers: { 'Content-Type': 'application/json' } },
          )
        }

        let params
        try {
          params = await chatParamsFromRequestBody(await request.json())
        } catch (error) {
          return new Response(
            error instanceof Error ? error.message : 'Bad request',
            { status: 400 },
          )
        }

        const abortController = new AbortController()

        try {
          // Merge the server tool set with any client-side tools the request
          // brought along (e.g. the showNxCommand UI tool).
          const mergedTools = mergeAgentTools(serverTools, params.tools)

          const options = createChatOptions({
            adapter: openRouterText(MODEL as any)
          })

          const stream = chat({
            ...options,
            tools: Object.values(mergedTools),
            systemPrompts: [SYSTEM_PROMPT],
            agentLoopStrategy: maxIterations(10),
            messages: params.messages,
            threadId: params.threadId,
            runId: params.runId,
            abortController,
          })

          return toServerSentEventsResponse(stream, { abortController })
        } catch (error: any) {
          if (error?.name === 'AbortError' || abortController.signal.aborted) {
            return new Response(null, { status: 499 })
          }
          console.error('[api/chat] error:', error)
          return new Response(
            JSON.stringify({ error: error?.message || 'An error occurred' }),
            { status: 500, headers: { 'Content-Type': 'application/json' } },
          )
        }
      },
    },
  },
})
