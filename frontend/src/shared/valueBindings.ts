/** Read effective value bindings consistently across card forms. */
import type { Card, Workflow } from "./types";
export interface ValueBinding {
  reference: string;
  path?: string;
  connected: boolean;
}
export function valueBinding(
  workflow: Workflow,
  graphId: string,
  card: Card,
  key: string,
): ValueBinding | null {
  const edge = workflow.graphs[graphId].edges.find(
    (item) =>
      item.kind === "value" &&
      item.target === card.id &&
      item.target_port === "config:" + key,
  );
  if (edge)
    return {
      reference: "card:" + edge.source,
      path: edge.path,
      connected: true,
    };
  const value = card.config?.[key];
  if (!value || typeof value !== "object" || !("$ref" in value)) return null;
  return {
    reference: String(value.$ref),
    path:
      "path" in value && typeof value.path === "string"
        ? value.path
        : undefined,
    connected: false,
  };
}
export function graphInputs(workflow: Workflow, graphId: string) {
  return graphId === "main"
    ? (workflow.inputs ?? {})
    : (Object.values(workflow.functions ?? {}).find(
        (item) => item.graph === graphId,
      )?.inputs ?? {});
}
