"use client";

import React from "react";
import { TextPart as TanStackTextPart } from "@tanstack/ai-react/ui";

export const TextPart = ({ part, ...props }: { part: any }) => (
  <TanStackTextPart
    content={part.text || ""}
    role={part.role}
    className="prose prose-sm max-w-none"
    userClassName="text-primary-foreground"
    assistantClassName="text-secondary-foreground"
    {...props}
  />
);
