"use server";

export async function generateImageAction(): Promise<{ presignedUrl: string }> {
  return { presignedUrl: "https://example.com/dummy.png" }
}
