"use client";

import { useState, useEffect } from "react";
import { vocabulary } from "@/messages/vocabulary";

export const BusyIndicator = ({
  label,
  labelAfterAWhile,
  thresholdMs = 35000,
}: {
  label: string;
  labelAfterAWhile: string;
  thresholdMs?: number;
}) => {
  const [isBusy, setIsBusy] = useState(false);
  const [showAfterAWhile, setShowAfterAWhile] = useState(false);

  useEffect(() => {
    if (!isBusy) {
      return;
    }

    const timer = setTimeout(() => {
      setShowAfterAWhile(true);
    }, thresholdMs);

    return () => clearTimeout(timer);
  }, [isBusy, thresholdMs]);

  return (
    <div className="mt-2 text-sm text-secondary-foreground">
      {showAfterAWhile ? labelAfterAWhile : label}
    </div>
  );
};