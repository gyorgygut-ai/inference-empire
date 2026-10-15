export const vocabulary = {
  meta: {
    name: "Face Value",
    description: "AI face transformation",
  },
  messages: {
    selectOutcome: "Select an outcome.",
    uploadReference: "Upload your photo...",
    uploadCta: "Click or drag & drop an image",
    outcomesAria: "Outcomes",

    working: "Working on it...",
    resultAlt: "Generated",
    download: "Download",
  },
  requestSelectedOutcome: {
    assistantMessage: "Select an outcome.",
  },
  requestReferenceImage: {
    assistantMessage: "Upload your photo...",
  },
  runGenerateImage: {
    requested: {
      assistantMessage: "Ready to generate. Approve to run inference.",
      userApprove: "Generate",
    },
    responded: {
      assistantMessage: "Approved. Generating...",
    },
    error: {
      assistantMessage: "Generation failed.",
    },
    streaming: {
      assistantMessage: "Working on it...",
    },
  },
}