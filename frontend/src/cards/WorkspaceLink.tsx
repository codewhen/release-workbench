import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { api } from "../shared/api";
import { useLocation } from "../navigation/location";
import type { Workflow } from "../shared/types";

export function WorkspaceLink({
  workflow,
  graphId,
  cardId,
  view,
  execution,
}: {
  workflow: Workflow;
  graphId: string;
  cardId: string;
  view: "edit" | "run";
  execution?: string;
}) {
  const route = useLocation();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [fallback, setFallback] = useState("");
  return (
    <div className="workspace-navigation">
      <button
        type="button"
        className="nodrag"
        disabled={busy}
        onClick={async () => {
          const tab = window.open("about:blank", "_blank");
          if (tab) tab.opener = null;
          setBusy(true);
          setError("");
          setFallback("");
          try {
            const result = await api<{ url: string }>(
              "open-workspace",
              { workflow, graph: graphId, card: cardId, view, execution },
              route.workflow!,
            );
            if (tab)
              tab.location.replace(new URL(result.url, location.origin).href);
            else setFallback(result.url);
          } catch (error) {
            tab?.close();
            setError(error instanceof Error ? error.message : String(error));
          } finally {
            setBusy(false);
          }
        }}
      >
        <ExternalLink size={15} />
        {busy ? "Opening child…" : "Open child workflow"}
      </button>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {fallback && (
        <a href={fallback} target="_blank" rel="noopener noreferrer">
          Open child workflow in a new tab
        </a>
      )}
      <small>
        {view === "run"
          ? "Opens this child execution when available, or its definition before it runs. This caller stays open."
          : "Opens the child definition in a new tab. This caller stays open."}
      </small>
    </div>
  );
}
