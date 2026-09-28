"use client";

import { type ImageMessagePart, type ImageMessagePartComponent } from "@assistant-ui/react";
import { DownloadIcon } from "lucide-react";

const dataUriToBlob = (dataUri: string): Blob | null => {
  const commaIndex = dataUri.indexOf(",");
  const meta = commaIndex >= 0 ? dataUri.slice(0, commaIndex) : dataUri;
  const data = commaIndex >= 0 ? dataUri.slice(commaIndex + 1) : "";
  const mime =
    meta.match(/data:([^;]+)/i)?.[1]?.toLowerCase() ?? "application/octet-stream";
  if (!/;base64/i.test(meta)) {
    const parts: BlobPart[] = [];
    let last = 0;
    for (const match of data.matchAll(/(?:%[\da-f]{2})+/gi)) {
      if (match.index > last) parts.push(data.slice(last, match.index));
      const run = match[0];
      const escaped = new Uint8Array(run.length / 3);
      for (let index = 0; index < escaped.length; index++) {
        escaped[index] = Number.parseInt(run.slice(index * 3 + 1, index * 3 + 3), 16);
      }
      parts.push(escaped);
      last = match.index + run.length;
    }
    parts.push(data.slice(last));
    return new Blob(parts, { type: mime });
  }
  let bytes: string;
  try {
    const base64 = data.replace(/%([\da-f]{2})/gi, (_match, hex: string) =>
      String.fromCharCode(Number.parseInt(hex, 16)),
    );
    bytes = atob(base64);
  } catch {
    return null;
  }
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new Blob([arr], { type: mime });
};

const mimeFromImage = (image: string): string | undefined =>
  image.match(/^data:([^;,]+)/i)?.[1]?.toLowerCase();

const defaultFilenameFromImage = (image: string): string => {
  const mime = mimeFromImage(image);
  if (mime) {
    const ext = mime.split("/")[1] ?? "png";
    return `image.${ext}`;
  }
  try {
    const path = new URL(image, document.baseURI).pathname;
    const encodedBasename = path.split("/").pop() ?? "";
    let basename = encodedBasename;
    try {
      basename = decodeURIComponent(encodedBasename);
    } catch {}
    if (/\.(png|jpe?g|webp|gif|svg)$/i.test(basename)) return basename;
  } catch {}
  return "image.png";
};

const downloadImagePart = (
  part: Pick<ImageMessagePart, "image" | "filename">,
): void => {
  if (typeof document === "undefined") return;
  const filename = part.filename ?? defaultFilenameFromImage(part.image);
  const isDataUri = /^data:/i.test(part.image);
  const blob = isDataUri ? dataUriToBlob(part.image) : null;
  if (isDataUri && !blob) return;
  const objectUrl = blob ? URL.createObjectURL(blob) : null;
  const href = objectUrl ?? part.image;
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  if (objectUrl) setTimeout(() => URL.revokeObjectURL(objectUrl), 40000);
};

export const Image: ImageMessagePartComponent = ({ image, filename, status }) => {
  if (status?.type === "running") {
    return (
      <div
        className="bg-muted/50 flex min-h-32 items-center justify-center p-4 rounded-lg"
        role="status"
        aria-label="Generating image…"
      >
        <svg className="text-muted-foreground size-8 animate-spin" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </div>
    );
  }

  if (status?.type === "incomplete" && status.reason === "content-filter") {
    return (
      <div className="bg-muted/50 flex min-h-32 flex-col items-center justify-center gap-2 p-4 rounded-lg">
        <svg className="text-muted-foreground size-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
        <p className="text-sm font-medium">Image could not be generated</p>
      </div>
    );
  }

  return (
    <div className="relative rounded-lg overflow-hidden border border-border bg-background">
      <img
        src={image}
        alt={filename ?? "Generated image"}
        className="block h-auto w-full object-contain"
        loading="lazy"
      />
      <div className="absolute bottom-0 right-0 m-2 flex gap-1">
        <button
          type="button"
          onClick={() => downloadImagePart({ image, filename })}
          aria-label="Download image"
          className="hover:bg-muted/80 inline-flex size-8 items-center justify-center rounded-lg bg-background/80 backdrop-blur-sm transition-colors"
        >
          <DownloadIcon className="size-4 text-foreground" />
        </button>
      </div>
      {filename && (
        <div className="absolute bottom-0 left-0 m-2 px-2 py-1 text-xs text-muted-foreground bg-background/80 backdrop-blur-sm rounded">
          {filename}
        </div>
      )}
    </div>
  );
};