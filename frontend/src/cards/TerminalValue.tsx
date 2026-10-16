import { Choice } from "../components/Choice";
import { JsonInput } from "../components/JsonInput";
import { valueBinding } from "../shared/valueBindings";
import { resultType } from "../shared/cards";
import type { Card, CardMeta, Workflow } from "../shared/types";

export function TerminalValue({
  card,
  workflow,
  graphId,
  catalog,
  disabled,
  onChange,
  onInvalid,
}: {
  card: Card;
  workflow: Workflow;
  graphId: string;
  catalog: CardMeta[];
  disabled: boolean;
  onChange: (key: string, value: unknown) => void;
  onInvalid?: (error: string) => void;
}) {
  const graph = workflow.graphs[graphId];
  const value = card.config?.value;
  const binding = valueBinding(workflow, graphId, card, "value");
  const reference = binding?.reference ?? "";
  const source = reference.startsWith("card:") ? reference.slice(5) : "";
  const mode =
    card.config?.returns === "void"
      ? "void"
      : source
        ? "card:" + source
        : reference
          ? "binding"
          : "literal";
  const candidates = graph.cards.filter(
    (c) =>
      c.id !== card.id &&
      !["finish", "return", "start"].includes(c.kind) &&
      resultType(
        c,
        catalog.find((m) => m.kind === c.kind)!,
        workflow,
      ) !== "void",
  );
  return (
    <div className="terminal-result">
      <label>
        Result source
        <Choice
          label="Result source"
          value={mode}
          disabled={disabled}
          options={[
            { value: "void", label: "No result (Void)" },
            { value: "literal", label: "Type a value" },
            ...(reference && mode === "binding"
              ? [
                  {
                    value: "binding",
                    label: "Existing input or environment binding",
                  },
                ]
              : []),
            ...candidates.map((c) => ({
              value: "card:" + c.id,
              label: "Result of “" + c.name + "”",
            })),
          ]}
          onChange={(selected) => {
            if (selected === "void") onChange("returns", "void");
            else if (selected === "literal") onChange("value", null);
            else if (selected.startsWith("card:"))
              onChange("value", { $ref: selected });
          }}
        />
      </label>
      {mode === "literal" && (
        <JsonInput
          label={card.kind === "finish" ? "Workflow output" : "Return value"}
          value={value}
          onChange={(v) => onChange("value", v)}
          disabled={disabled}
          onInvalid={onInvalid}
        />
      )}
      {source && (
        <small>
          Uses this card’s result when this completion marker runs. The source
          must execute first; no extra value wire is needed.
        </small>
      )}
      <small>
        {card.kind === "finish"
          ? "Finish ends the main workflow. Its result is optional."
          : "Return completes this function or control branch and sends its result back to the caller."}
      </small>
    </div>
  );
}
