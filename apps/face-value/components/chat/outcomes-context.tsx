"use client";

import React from "react";
import type { PublicOutcome } from "@/outcomes/outcomes";

const OutcomesContext = React.createContext<PublicOutcome[]>([]);

export const usePublicOutcomes = () => React.useContext(OutcomesContext);

export const OutcomesProvider = ({
  outcomes,
  children,
}: {
  outcomes: PublicOutcome[];
  children: React.ReactNode;
}) => <OutcomesContext.Provider value={outcomes}>{children}</OutcomesContext.Provider>;
