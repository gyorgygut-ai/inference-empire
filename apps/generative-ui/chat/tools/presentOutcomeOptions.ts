import { toolDefinition } from "@tanstack/ai"

export const presentOutcomeOptionsDef = toolDefinition({
  name: "presentOutcomeOptions",
  description: "Present outcome options in a two-column grid sorted by order",
  inputSchema: {
    type: "object",
    properties: {},
  },
  outputSchema: {
    type: "object",
    properties: {
      outcomeId: { type: "string" },
    },
    required: ["outcomeId"],
  },
})
