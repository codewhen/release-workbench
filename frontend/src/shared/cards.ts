import type { Card, CardMeta } from "./types";
/** Display registry defaults without turning an untouched saved document into a draft. */
export function configuredCard(card: Card, meta: CardMeta): Card {
  return { ...card, config: { ...meta.defaults, ...card.config } };
}

export function resultType(
  card: Card,
  meta: CardMeta,
  workflow: import("./types").Workflow,
): string {
  if (["python", "return", "finish"].includes(card.kind))
    return String(card.config?.returns ?? meta.defaults.returns ?? meta.output);
  if (card.kind === "call")
    return (
      workflow.functions?.[String(card.config?.function)]?.returns ?? "json"
    );
  if (card.kind === "variable")
    return workflow.globals?.[String(card.config?.name)]?.type ?? "json";
  if (card.kind === "manual")
    return card.config?.mode === "approval" ? "void" : "boolean";
  return meta.output;
}
