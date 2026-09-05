import { PanelLeft, PanelRight } from "lucide-react";

interface MainProps {
  onToggleLeft: () => void;
  onToggleRight: () => void;
}

export function Main({ onToggleLeft, onToggleRight }: MainProps) {
  return (
    <section className="flex h-full min-h-0 flex-col bg-background">
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-border px-3">
        <button
          type="button"
          aria-label="Toggle Workers"
          onClick={onToggleLeft}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-medium text-foreground mx-2">Chat</span>
        <button
          type="button"
          aria-label="Toggle Artifacts"
          onClick={onToggleRight}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <PanelRight className="h-4 w-4" />
        </button>
      </header>
      <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Chat UI placeholder
      </div>
    </section>
  );
}
