import { toolDefinition } from "@tanstack/ai"

export const presentOutcomeOptionsDef = toolDefinition({
  name: "presentOutcomeOptions",
  description: "Present outcome options in a two-column grid sorted by order",
  inputSchema: {
    type: "object",
    properties: {
      outcomes: {
        type: "array",
        items: {
          type: "object",
          properties: {
            id: { type: "string" },
            title: { type: "string" },
            order: { type: "number" },
          },
          required: ["id", "title", "order"],
        },
      },
    },
    required: ["outcomes"],
  },
  outputSchema: {
    type: "object",
    properties: {
      outcomeId: { type: "string" },
    },
    required: ["outcomeId"],
  },
})
