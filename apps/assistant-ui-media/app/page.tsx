"use client";

import React, { useCallback, useState } from "react";

const Home = () => {
  const [prompt, setPrompt] = useState("A golden retriever wearing a top hat");
  const [image, setImage] = useState<string | null>(null);
  const [revisedPrompt, setRevisedPrompt] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(async (p: string) => {
    setIsGenerating(true);
    setError(null);
    setRevisedPrompt(null);
    setImage(null);
    try {
      const res = await fetch("/api/image", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ prompt: p }),
      });
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const result = (await res.json()) as {
        image: string;
        metadata?: { revisedPrompt?: string };
      };
      setImage(result.image);
      if (typeof result.metadata?.revisedPrompt === "string") {
        setRevisedPrompt(result.metadata.revisedPrompt);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsGenerating(false);
    }
  }, []);

  return (
    <main className="mx-auto flex h-full max-w-xl flex-col gap-4 p-6">
      <header>
        <h1 className="text-xl font-semibold">Image Generation</h1>
        <p className="text-muted-foreground text-sm">
          Calls a server route that submits to the Flux2 router worker
          (<code>POST /infer</code>, poll <code>GET /inquire?id=</code>) and
          renders the result inline.
        </p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void generate(prompt);
        }}
        className="flex gap-2"
      >
        <input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe an image…"
          className="flex-1 rounded border px-3 py-2"
        />
        <button
          type="submit"
          disabled={isGenerating || !prompt.trim()}
          className="bg-primary text-primary-foreground rounded px-3 py-2 disabled:opacity-50"
        >
          {isGenerating ? "Generating…" : "Generate"}
        </button>
      </form>

      {error && (
        <p className="text-destructive text-sm" role="alert">
          {error}
        </p>
      )}

      {isGenerating && (
        <div className="flex items-center justify-center rounded-lg border p-8 text-muted-foreground">
          Generating…
        </div>
      )}

      {image && (
        <div className="space-y-2">
          <img
            src={image}
            alt="Generated"
            className="w-full rounded-lg border object-contain"
          />
          {revisedPrompt && (
            <p className="text-muted-foreground text-xs">
              <strong>Revised prompt:</strong> {revisedPrompt}
            </p>
          )}
        </div>
      )}
    </main>
  );
};

export default Home;