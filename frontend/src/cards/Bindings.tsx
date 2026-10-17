import { useState } from "react";
import type { Card, Workflow } from "../shared/types";
import { Choice } from "../components/Choice";
import { JsonInput } from "../components/JsonInput";
export function Bindings({
  card,
  workflow,
  graphId,
  onChange,
  disabled,
}: {
  card: Card;
  workflow: Workflow;
  graphId: string;
  onChange: (values: Record<string, unknown>) => void;
  disabled: boolean;
}) {
  const [name, setName] = useState("");
  const definition = Object.values(workflow.functions ?? {}).find(
    (f) => f.graph === graphId,
  );
  const inputNames = Object.keys(
    graphId === "main" ? (workflow.inputs ?? {}) : (definition?.inputs ?? {}),
  );
  const choices = [
    ...inputNames.map((id) => ({
      value: "input:" + id,
      label: "Input · " + id,
    })),
    ...workflow.graphs[graphId].cards
      .filter((c) => c.id !== card.id)
      .map((c) => ({ value: "card:" + c.id, label: "Card · " + c.name })),
    { value: "loop", label: "Current loop" },
    { value: "error", label: "Caught error" },
  ];
  return (
    <section>
      <h3>Named inputs</h3>
      <p className="muted">
        Python receives these as inputs. Function calls pass them as arguments.
        Graph connections can supply them too.
      </p>
      {Object.entries(card.inputs ?? {}).map(([key, value]) => {
        const binding =
          typeof value === "object" && value !== null && "$ref" in value
            ? (value as { $ref: string; path?: string })
            : null;
        return (
          <div className="binding" key={key}>
            <strong>{key}</strong>
            <label>
              Value from
              <Choice
                label={key + " source"}
                value={binding?.$ref ?? "constant"}
                disabled={disabled}
                options={[
                  { value: "constant", label: "A value I enter" },
                  ...choices,
                ]}
                onChange={(source) =>
                  onChange({
                    ...card.inputs,
                    [key]: source === "constant" ? null : { $ref: source },
                  })
                }
              />
            </label>
            {binding ? (
              <label>
                Field path (optional)
                <input
                  disabled={disabled}
                  value={binding.path ?? ""}
                  onChange={(e) =>
                    onChange({
                      ...card.inputs,
                      [key]: { ...binding, path: e.target.value },
                    })
                  }
                />
              </label>
            ) : (
              <JsonInput
                label={key + " value"}
                disabled={disabled}
                value={value}
                onChange={(v) => onChange({ ...card.inputs, [key]: v })}
              />
            )}
            <button
              disabled={disabled}
              onClick={() => {
                const next = { ...card.inputs };
                delete next[key];
                onChange(next);
              }}
            >
              Remove input
            </button>
          </div>
        );
      })}
      <label>
        New input name
        <input
          value={name}
          disabled={disabled}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <button
        disabled={disabled || !name || Object.hasOwn(card.inputs ?? {}, name)}
        onClick={() => {
          onChange({ ...card.inputs, [name]: null });
          setName("");
        }}
      >
        Add input
      </button>
    </section>
  );
}
