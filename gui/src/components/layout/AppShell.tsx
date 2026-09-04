"use client"

import { useReducer } from "react"
import { Workers } from "@/components/panels/Workers"
import { Artifacts } from "@/components/panels/Artifacts"
import { Main } from "@/components/panels/Main"

type State = { opened: "left" | "right" | null }
type Action = { type: "TOGGLE_LEFT" } | { type: "TOGGLE_RIGHT" } | { type: "CLOSE" }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "TOGGLE_LEFT":
      return { opened: state.opened === "left" ? null : "left" }
    case "TOGGLE_RIGHT":
      return { opened: state.opened === "right" ? null : "right" }
    case "CLOSE":
      return { opened: null }
    default:
      return state
  }
}

export function AppShell() {
  const [state, dispatch] = useReducer(reducer, { opened: null })
  const leftOpen = state.opened === "left"
  const rightOpen = state.opened === "right"

  return (
    <div className="flex h-dvh">
      {leftOpen && <Workers open={leftOpen} onOpenChange={() => dispatch({ type: "TOGGLE_LEFT" })} />}
      <div className="min-w-0 flex-1">
        <Main
          onToggleLeft={() => dispatch({ type: "TOGGLE_LEFT" })}
          onToggleRight={() => dispatch({ type: "TOGGLE_RIGHT" })}
        />
      </div>
      <Artifacts open={rightOpen} onOpenChange={() => dispatch({ type: "TOGGLE_RIGHT" })} className="lg:flex-1 lg:w-auto lg:[&_[data-slot=collapsible-content]]:!block" />
    </div>
  )
}
