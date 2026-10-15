import type { Card, CardMeta } from "./types";
/** Display registry defaults without turning an untouched saved document into a draft. */
export function configuredCard(card: Card, meta: CardMeta): Card {
  return { ...card, config: { ...meta.defaults, ...card.config } };
}
