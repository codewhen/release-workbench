import { describe, it, expect } from "vitest";
import { setCardConfiguration } from "./cardCommands";
import type { CardMeta, Workflow } from "../shared/types";
const catalog: CardMeta[] = [
  {
    kind: "python",
    label: "Python",
    category: "External",
    defaults: { returns: "boolean" },
    output: "json",
    fields: [],
    ports: ["next"],
  },
  {
    kind: "finish",
    label: "Finish",
    category: "Functions",
    defaults: { returns: "void", value: null },
    output: "json",
    fields: [],
    ports: [],
  },
];
const workflow = (): Workflow => ({
  version: 3,
  name: "Commands",
  graphs: {
    main: {
      cards: [
        {
          id: "source",
          name: "Python",
          kind: "python",
          config: { returns: "boolean" },
        },
        {
          id: "finish",
          name: "Finish",
          kind: "finish",
          config: { returns: "void" },
        },
      ],
      edges: [
        {
          id: "value",
          kind: "value",
          source: "source",
          source_port: "value",
          target: "finish",
          target_port: "config:value",
        },
      ],
    },
  },
});
describe("card configuration commands", () => {
  it("binds a result and replaces an older value wire without mutating the source", () => {
    const original = workflow();
    const next = setCardConfiguration(
      original,
      "main",
      "finish",
      "value",
      { $ref: "card:source" },
      catalog,
    );
    expect(next.graphs.main.cards[1].config).toEqual({
      returns: "boolean",
      value: { $ref: "card:source" },
    });
    expect(next.graphs.main.edges).toEqual([]);
    expect(original.graphs.main.edges).toHaveLength(1);
  });
  it("Void clears the selected value and incoming value wire", () => {
    const next = setCardConfiguration(
      workflow(),
      "main",
      "finish",
      "returns",
      "void",
      catalog,
    );
    expect(next.graphs.main.cards[1].config).toEqual({
      returns: "void",
      value: null,
    });
    expect(next.graphs.main.edges).toEqual([]);
  });
  it("a field edit preserves unrelated value connections", () => {
    const original = workflow();
    const next = setCardConfiguration(
      original,
      "main",
      "source",
      "code",
      "return True",
      catalog,
    );
    expect(next.graphs.main.cards[0].config?.code).toBe("return True");
    expect(original.graphs.main.cards[0].config?.code).toBeUndefined();
    expect(next.graphs.main.edges).toHaveLength(1);
  });
  it("rejects edits to a nonexistent card", () => {
    expect(() =>
      setCardConfiguration(workflow(), "main", "missing", "value", 0, catalog),
    ).toThrow("Card does not exist");
  });
});
