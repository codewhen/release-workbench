import type { Workflow } from "../shared/types";
import { navigate, useLocation } from "./location";

export function useEditorLocation(workflow: Workflow, recovered: boolean) {
  const route = useLocation();
  const graphId =
    route.graph && workflow.graphs[route.graph] ? route.graph : "main";
  const selected =
    workflow.graphs[graphId].cards.some((card) => card.id === route.card) ||
    workflow.layout?.[graphId]?.areas?.some((area) => area.id === route.card)
      ? route.card!
      : null;
  return {
    graphId,
    setGraphId: (graph: string, replace = false) => {
      if (graph === graphId) return;
      navigate(
        {
          graph: graph === "main" ? undefined : graph,
          card: undefined,
          panel: undefined,
        },
        replace,
      );
    },
    view: route.view ?? (recovered ? "edit" : "run"),
    setView: (view: "run" | "edit") => navigate({ view }),
    representation: route.display ?? (innerWidth < 1000 ? "list" : "canvas"),
    setRepresentation: (display: "canvas" | "list" | "yaml") =>
      navigate({ display }),
    selected,
    setSelected: (card: string | null) =>
      navigate({ card: card ?? undefined }, true),
    settings: route.panel === "settings",
    setSettings: (settings: boolean) =>
      navigate({ panel: settings ? "settings" : undefined }),
  };
}
