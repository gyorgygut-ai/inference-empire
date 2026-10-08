import {
  BaseFilesAdapter,
  normalizeFileUploadInput,
  type FileHandle,
  type FileUploadInput,
} from "@tanstack/ai/adapters";

const MAX_BYTES = 5 * 1024 * 1024;

const blobs = new Map<string, { blob: Blob; mimeType: string; filename: string }>();

export class Flux2FilesAdapter extends BaseFilesAdapter<"flux2"> {
  readonly name = "flux2" as const;

  async upload(input: FileUploadInput): Promise<FileHandle<"flux2">> {
    const { blob, mimeType, filename } = normalizeFileUploadInput(input);
    const type = mimeType ?? blob.type;
    if (!type.startsWith("image/")) {
      throw new Error("Unsupported file type");
    }
    if (blob.size > MAX_BYTES) {
      throw new Error("File exceeds size limit");
    }
    const id = crypto.randomUUID();
    const name = filename ?? (blob instanceof File ? blob.name : "reference.jpg");
    blobs.set(id, { blob, mimeType: type, filename: name });
    return { id, provider: "flux2", mimeType: type, sizeBytes: blob.size, filename: name };
  }

  async get(id: string): Promise<FileHandle<"flux2">> {
    const entry = blobs.get(id);
    if (!entry) {
      throw new Error("Unknown file handle");
    }
    return {
      id,
      provider: "flux2",
      mimeType: entry.mimeType,
      sizeBytes: entry.blob.size,
      filename: entry.filename,
    };
  }

  async delete(id: string): Promise<void> {
    blobs.delete(id);
  }
}

export const flux2Files = new Flux2FilesAdapter();

export function getFlux2FileBlob(id: string): Blob | undefined {
  return blobs.get(id)?.blob;
}
