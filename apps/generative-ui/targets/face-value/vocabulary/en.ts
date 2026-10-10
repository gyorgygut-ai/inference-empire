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
    userPickedOutcome: "I want {title}",
    requestInference: "Let's do this!",
    busy: "",
    working: "Working on it...",
    busyForAWhile: "🧽 You've been queued. Inference ain't cheap...",
    timeout: "Server timeout",
    rejected: "🫷🏻 The server rejected this request.",
    sizeLimit: "Image exceeds size limit",
    fulfilled: "Done!",
    resultAlt: "Generated",
    download: "Download",
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