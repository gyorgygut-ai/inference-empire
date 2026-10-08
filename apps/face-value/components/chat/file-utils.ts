export interface ReferenceImage { base64: string; mimeType: string }

export const readFileAsData = (file: File): Promise<ReferenceImage> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error("Reference image unreadable"))
    reader.onload = () => {
      const url = String(reader.result ?? "")
      const match = /^data:([\w/-]+);base64,(.+)$/.exec(url)
      if (!match) { return reject(new Error("Reference image unreadable")) }
      resolve({ base64: match[2], mimeType: match[1] })
    }
    reader.readAsDataURL(file)
  })