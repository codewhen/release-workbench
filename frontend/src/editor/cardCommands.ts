/** Pure card configuration edits, independent from React component state. */
import type { CardMeta, Workflow } from "../shared/types";
import { resultType } from "../shared/cards";
import { clone } from "./model";
export function setCardConfiguration(
  workflow: Workflow,
  graphId: string,
  id: string,
  key: string,
  value: unknown,
  catalog: CardMeta[],
): Workflow {
  const next = clone(workflow),
    graph = next.graphs[graphId];
  const card = graph.cards.find((item) => item.id === id);
  if (!card) throw Error("Card does not exist.");
  let targetKey = key;
  if (
    ["finish", "return"].includes(card.kind) &&
    (key === "value" || (key === "returns" && value === "void"))
  ) {
    const config: Record<string, unknown> = {
      ...catalog.find((meta) => meta.kind === card.kind)!.defaults,
      ...card.config,
      value,
    };
    const reference =
      value && typeof value === "object" && "$ref" in value
        ? String(value.$ref)
        : "";
    const source = graph.cards.find((item) => reference === "card:" + item.id);
    if (key === "returns") {
      config.returns = "void";
      config.value = null;
    } else if (source)
      config.returns = resultType(
        source,
        catalog.find((meta) => meta.kind === source.kind)!,
        next,
      );
    else if (config.returns === "void") config.returns = "json";
    card.config = config;
    targetKey = "value";
  } else card.config = { ...card.config, [key]: value };
  graph.edges = graph.edges.filter(
    (edge) =>
      !(
        edge.kind === "value" &&
        edge.target === id &&
        edge.target_port === "config:" + targetKey
      ),
  );
  return next;
}
