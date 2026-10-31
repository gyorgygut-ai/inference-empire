export const vocabulary = {
  meta: {
    name: "Face Value",
    description: "Face - Value",
  },
  messages: {
    selectOutcome: "Select an outcome.",
    uploadReference: "Upload your photo...",
    uploadCta: "Click || drop",
    outcomesAria: "Outcomes",

    working: "Working on it...",
    resultAlt: "Generated",
  },
  requestSelectedOutcome: {
    assistantMessage: "Select an outcome:",
  },
  requestReferenceImage: {
    assistantMessage: "Upload your photo...",
  },
  runGenerateImage: {
    requested: {
      assistantMessage: "Ready?",
      userApprove: "Generate Image",
    },
    responded: {
      assistantMessage: "Approved. Generating...",
    },
    error: {
      assistantMessage: "Request failed.",
    },
    streaming: {
      assistantMessage: "Working on it...",
    },
  },
}
