import { useState } from "react";
import type { Connection } from "@xyflow/react";
import type { Card, Workflow, CardMeta } from "../shared/types";
import { Choice } from "../components/Choice";
import { flowOutputs } from "./CardNode";
export function Connections({
  workflow,
  graphId,
  card,
  meta,
  catalog,
  disabled,
  onConnect,
  onDelete,
}: {
  workflow: Workflow;
  graphId: string;
  card: Card;
  meta: CardMeta;
  catalog: CardMeta[];
  disabled: boolean;
  onConnect: (connection: Connection) => void;
  onDelete: (edge: string) => void;
}) {
  const [sourcePort, setSourcePort] = useState("next"),
    [target, setTarget] = useState(""),
    [targetPort, setTargetPort] = useState("entry");
  const [kind, setKind] = useState("flow"),
    [valuePort, setValuePort] = useState("");
  const graph = workflow.graphs[graphId],
    targetCard = graph.cards.find((c) => c.id === target);
  const outputs = flowOutputs(card, meta);
  return (
    <section className="connection-form">
      <h3>Connections</h3>
      {graph.edges
        .filter((e) => e.source === card.id || e.target === card.id)
        .map((e) => (
          <div key={e.id}>
            <small>
              {e.source}.{e.source_port ?? "next"} → {e.target}.
              {e.target_port ?? "entry"} ({e.kind ?? "flow"})
            </small>
            <button disabled={disabled} onClick={() => onDelete(e.id)}>
              Disconnect
            </button>
          </div>
        ))}
      <label>
        Connection type
        <Choice
          label="Connection type"
          value={kind}
          disabled={disabled}
          onChange={setKind}
          options={[
            { value: "flow", label: "Execution" },
            { value: "value", label: "Typed value" },
          ]}
        />
      </label>
      {kind === "value" && (
        <>
          <label>
            Value receiver
            <Choice
              label="Value receiver"
              disabled={disabled}
              value={target}
              onChange={setTarget}
              options={[
                { value: "", label: "Choose a card…" },
                ...graph.cards
                  .filter((c) => c.id !== card.id && c.kind !== "start")
                  .map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
          </label>
          <label>
            Value input
            <Choice
              label="Value input"
              disabled={disabled}
              value={valuePort}
              onChange={setValuePort}
              options={[
                { value: "", label: "Choose a field…" },
                ...(
                  catalog.find((m) => m.kind === targetCard?.kind)?.fields ?? []
                )
                  .filter((f) =>
                    ["json", "number", "text", "textarea"].includes(f.widget),
                  )
                  .map((f) => ({ value: "config:" + f.key, label: f.label })),
                ...Object.keys(
                  workflow.functions?.[String(targetCard?.config?.function)]
                    ?.inputs ?? {},
                ).map((name) => ({
                  value: "input:" + name,
                  label: "Argument · " + name,
                })),
              ]}
            />
          </label>
          <button
            disabled={disabled || !target || !valuePort}
            onClick={() =>
              onConnect({
                source: card.id,
                target,
                sourceHandle: "value",
                targetHandle: "value:" + valuePort,
              })
            }
          >
            Connect value
          </button>
          <small>
            Wire the producer before the receiver in execution order. Use Named
            inputs for nested field selection.
          </small>
        </>
      )}
      {kind === "flow" && outputs.length > 0 && (
        <>
          <label>
            Execution output
            <Choice
              label="Execution output"
              value={sourcePort}
              disabled={disabled}
              onChange={setSourcePort}
              options={outputs.map((value) => ({ value, label: value }))}
            />
          </label>
          <label>
            Connect to
            <Choice
              label="Connect to card"
              value={target}
              disabled={disabled}
              onChange={setTarget}
              options={[
                { value: "", label: "Choose a card…" },
                ...graph.cards
                  .filter((c) => c.id !== card.id && c.kind !== "start")
                  .map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
          </label>
          <label>
            Target port
            <Choice
              label="Target port"
              value={targetPort}
              disabled={disabled}
              onChange={setTargetPort}
              options={[
                { value: "entry", label: "Entry" },
                ...(targetCard?.kind === "loop"
                  ? [{ value: "next_iteration", label: "Next iteration" }]
                  : []),
              ]}
            />
          </label>
          <button
            disabled={disabled || !target}
            onClick={() =>
              onConnect({
                source: card.id,
                target,
                sourceHandle:
                  "flow:" +
                  (outputs.includes(sourcePort) ? sourcePort : outputs[0]),
                targetHandle: "flow:" + targetPort,
              })
            }
          >
            Connect execution
          </button>
        </>
      )}
    </section>
  );
}
