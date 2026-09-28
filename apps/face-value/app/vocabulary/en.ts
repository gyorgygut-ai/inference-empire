export const vocabulary = {
  steps: {
    outcome: {
      message: "Select an outcome",
    },
    reference: {
      message: "Upload a reference image",
    },
    generate: {
      label: "Generate",
    },
  },
} as const;

export type Vocabulary = typeof vocabulary;