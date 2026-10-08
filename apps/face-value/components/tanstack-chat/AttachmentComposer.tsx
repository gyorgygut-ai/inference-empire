"use client";

import React, { useRef, useState, useCallback } from "react";
import { ImageIcon, XIcon } from "lucide-react";
import { vocabulary } from "@/messages/vocabulary";
import { useChatContext } from "./ChatProvider";

export const AttachmentComposer = () => {
  const { referenceFile, setReferenceFile } = useChatContext();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isAttachmentUploadEnabled = !referenceFile;

  const handleFileSelect = useCallback((file: File | null) => {
    setReferenceFile(file);
  }, [setReferenceFile]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0] || null;
      if (file && file.type.startsWith("image/")) {
        handleFileSelect(file);
      }
      e.target.value = "";
    },
    [handleFileSelect]
  );

  const removeAttachment = () => {
    handleFileSelect(null);
  };

  return (
    <div
      className={`rounded-xl border-2 border-dashed transition-colors ${
        isDragging ? "border-primary bg-primary/5" : "border-border"
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleInputChange}
        className="hidden"
        disabled={!isAttachmentUploadEnabled}
      />

      {referenceFile ? (
        <div className="flex items-center gap-2 rounded-lg border p-2 m-2 bg-background">
          <div className="flex size-10 items-center justify-center overflow-hidden rounded bg-muted text-xs">
            <ImageIcon className="size-4" />
          </div>
          <span className="min-w-0 flex-1 truncate text-sm text-secondary-foreground">
            {referenceFile.name}
          </span>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              removeAttachment();
            }}
            className="ml-auto rounded-full p-1 hover:bg-muted"
            aria-label="Remove attachment"
          >
            <XIcon className="size-3" />
          </button>
        </div>
      ) : (
        <div className="py-6 text-center">
          <ImageIcon className="mx-auto size-8 text-muted-foreground" />
          <p className="mt-2 text-sm text-secondary-foreground">
            {vocabulary.messages.uploadReference}
          </p>
          <p className="text-xs text-muted-foreground">
            Click or drag & drop an image
          </p>
        </div>
      )}
    </div>
  );
};