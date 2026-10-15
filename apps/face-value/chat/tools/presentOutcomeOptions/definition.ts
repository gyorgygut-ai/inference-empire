import { toolDefinition } from "@tanstack/ai";
import { z } from "zod";

export const presentOutcomeOptionsDef = toolDefinition({
  name: "presentOutcomeOptions",
  description: "Present outcome options in a two-column grid sorted by order",
  inputSchema: z.object({
    outcomes: z.array(
      z.object({
        id: z.string(),
        title: z.string(),
        order: z.number(),
      }),
    ),
  }),
  outputSchema: z.object({
    outcomeId: z.string(),
  }),
});
