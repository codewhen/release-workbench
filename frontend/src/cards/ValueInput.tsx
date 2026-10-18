import { Choice } from "../components/Choice";
import { JsonInput } from "../components/JsonInput";
import { valueBinding, graphInputs } from "../shared/valueBindings";
import { resultType } from "../shared/cards";
import type { Card, CardMeta, Field, Workflow } from "../shared/types";

export function ValueInput({
  field,
  card,
  graphId,
  catalog,
  workflow,
  disabled,
  onChange,
  onInvalid,
}: {
  field: Field;
  card: Card;
  graphId: string;
  catalog: CardMeta[];
  workflow: Workflow;
  disabled: boolean;
  onChange: (value: unknown) => void;
  onInvalid?: (error: string) => void;
}) {
  const graph = workflow.graphs[graphId];
  const value = card.config?.[field.key];
  const binding = valueBinding(workflow, graphId, card, field.key);
  const reference = binding?.reference ?? "";
  const predecessors = new Set<string>();
  const visit = (id: string) => {
    for (const e of graph.edges)
      if (
        e.kind === "flow" &&
        e.target === id &&
        e.target_port !== "next_iteration" &&
        !predecessors.has(e.source)
      ) {
        predecessors.add(e.source);
        visit(e.source);
      }
  };
  visit(card.id);
  const inputs = graphInputs(workflow, graphId);
  const options = [
    { value: "literal", label: "Type a value" },
    { value: "runtime:python", label: "Workbench Python executable" },
    ...graph.cards
      .filter(
        (c) =>
          c.id !== card.id &&
          !["start", "finish", "return"].includes(c.kind) &&
          (predecessors.has(c.id) || reference === "card:" + c.id) &&
          resultType(
            c,
            catalog.find((m) => m.kind === c.kind)!,
            workflow,
          ) !== "void",
      )
      .map((c) => ({
        value: "card:" + c.id,
        label: "Result of “" + c.name + "”",
      })),
    ...Object.keys(inputs).map((name) => ({
      value: "input:" + name,
      label: "Input “" + name + "”",
    })),
  ];
  const known = options.some((option) => option.value === reference);
  if (reference && !known)
    options.push({ value: reference, label: "Existing reference (advanced)" });
  const path = binding?.path;
  return (
    <div className="value-input">
      <label>
        {field.label} source
        <Choice
          label={field.label + " source"}
          value={reference || "literal"}
          disabled={disabled}
          options={options}
          onChange={(source) => {
            onInvalid?.("");
            onChange(
              source === "literal"
                ? (catalog.find((m) => m.kind === card.kind)?.defaults[
                    field.key
                  ] ?? null)
                : { $ref: source },
            );
          }}
        />
      </label>
      {!reference ? (
        <JsonInput
          label={field.label}
          value={value}
          onChange={onChange}
          disabled={disabled}
          multiline={field.advanced}
          onInvalid={onInvalid}
        />
      ) : (
        <>
          {path && <small>Field: {path}</small>}
          <details>
            <summary>Advanced reference</summary>
            <JsonInput
              label={field.label + " reference"}
              value={
                binding?.connected
                  ? { $ref: reference, ...(path ? { path } : {}) }
                  : value
              }
              onChange={onChange}
              disabled={disabled}
              onInvalid={onInvalid}
            />
          </details>
        </>
      )}
    </div>
  );
}
