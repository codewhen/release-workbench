import { describe, it, expect } from "vitest";
import type { Workflow } from "./types";
import { valueBinding, graphInputs } from "./valueBindings";
const workflow = (): Workflow => ({
  version: 3,
  name: "Values",
  inputs: { top: { type: "number" } },
  functions: {
    check: {
      graph: "check",
      returns: "boolean",
      inputs: { local: { type: "string" } },
    },
  },
  graphs: { main: { cards: [], edges: [] }, check: { cards: [], edges: [] } },
});
describe("effective value bindings", () => {
  it("preserves a stored reference and nested path", () => {
    const card = {
      id: "use",
      name: "Use",
      kind: "calculate" as const,
      config: { left: { $ref: "card:source", path: "items.0" } },
    };
    expect(valueBinding(workflow(), "main", card, "left")).toEqual({
      reference: "card:source",
      path: "items.0",
      connected: false,
    });
  });
  it("a connected value takes precedence over a stored literal or reference", () => {
    const value = workflow();
    value.graphs.main.edges = [
      {
        id: "bound",
        kind: "value",
        source: "new",
        target: "use",
        source_port: "value",
        target_port: "config:left",
        path: "answer",
      },
    ];
    expect(
      valueBinding(
        value,
        "main",
        {
          id: "use",
          name: "Use",
          kind: "calculate",
          config: { left: { $ref: "card:old" } },
        },
        "left",
      ),
    ).toEqual({ reference: "card:new", path: "answer", connected: true });
  });
  it("False, zero and null remain constants", () => {
    for (const left of [false, 0, null])
      expect(
        valueBinding(
          workflow(),
          "main",
          { id: "use", name: "Use", kind: "calculate", config: { left } },
          "left",
        ),
      ).toBeNull();
  });
  it("function pickers expose their local inputs rather than workflow inputs", () => {
    const value = workflow();
    expect(Object.keys(graphInputs(value, "main"))).toEqual(["top"]);
    expect(Object.keys(graphInputs(value, "check"))).toEqual(["local"]);
  });
});
