export function createSharpStub(resizedBuffer: Buffer) {
  return {
    resize: () => ({
      toBuffer: async () => resizedBuffer
    })
  }
}
