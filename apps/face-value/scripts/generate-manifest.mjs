import { readFileSync } from "node:fs"
import { join } from "node:path"

const vocabPath = join(process.cwd(), "messages", "vocabulary", "en.ts")
const vocabContent = readFileSync(vocabPath, "utf-8")

// Extract meta object from vocabulary.ts using regex
const metaMatch = vocabContent.match(/meta:\s*\{([^}]+)\}/s)
if (!metaMatch) {
  throw new Error("Could not extract meta from vocabulary.ts")
}

const metaStr = "{" + metaMatch[1].trim() + "}"
const meta = eval(`(${metaStr})`)

const manifest = {
  name: meta.name,
  short_name: meta.name,
  description: meta.description,
  start_url: "/",
  display: "standalone",
  background_color: "#ffffff",
  theme_color: "#000000",
  icons: [
    { src: "/android-chrome-192x192.png", sizes: "192x192", type: "image/png", purpose: "any maskable" },
    { src: "/android-chrome-512x512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
  ],
}

const outputPath = join(process.cwd(), "public", "site.webmanifest")
const output = JSON.stringify(manifest, null, 2) + "\n"
import { writeFileSync } from "node:fs"
writeFileSync(outputPath, output)
console.log("Manifest generated:", outputPath)