export const vocabulary = {
  messages: {
    selectOutcome: "Select an outcome to transform your face",
    uploadReference: "Upload a reference image",
    requestInference: "Generate",
    busy: "Generating…",
    rejected: "Generation rejected",
    done: "Done",
  },
  steps: {
    outcome: { message: "Select an outcome to transform your face" },
    reference: { message: "Upload a reference image" },
    generate: { label: "Generate", message: "Generating…" },
  },
  feedback: {
    missingImage: "Please upload a reference image",
    sizeLimit: "Image exceeds size limit",
    workerError: "Service temporarily unavailable",
    rejected: "Generation rejected",
    timeout: "Server timeout",
  },
}
