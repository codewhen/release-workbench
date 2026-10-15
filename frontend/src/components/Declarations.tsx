import { useState } from "react";
import { Choice } from "./Choice";
import { JsonInput } from "./JsonInput";
import { VALUE_TYPES } from "../shared/types";
export function Declarations({
  values,
  onChange,
  globals = false,
  disabled = false,
}: {
  values: Record<
    string,
    { type: string; default?: unknown; initial?: unknown }
  >;
  onChange: (
    values: Record<
      string,
      { type: string; default?: unknown; initial?: unknown }
    >,
  ) => void;
  globals?: boolean;
  disabled?: boolean;
}) {
  const [newName, setNewName] = useState("");
  const [error, setError] = useState("");
  const key = globals ? "initial" : "default";
  return (
    <div className="declarations">
      {Object.entries(values).map(([name, value]) => (
        <div className="declaration" key={name}>
          <strong>{name}</strong>
          <label>
            Type
            <Choice
              label={name + " type"}
              value={value.type}
              options={VALUE_TYPES.filter((t) => t !== "void").map((t) => ({
                value: t,
                label: t,
              }))}
              disabled={disabled}
              onChange={(type) =>
                onChange({ ...values, [name]: { ...value, type } })
              }
            />
          </label>
          <JsonInput
            label={globals ? "Initial value" : "Default value"}
            value={value[key]}
            onChange={(v) =>
              onChange({ ...values, [name]: { ...value, [key]: v } })
            }
            disabled={disabled}
          />
          {!globals && (
            <label className="check">
              <input
                type="checkbox"
                checked={!("default" in value)}
                disabled={disabled}
                onChange={(e) => {
                  const next = { ...value };
                  if (e.target.checked) delete next.default;
                  else next.default = null;
                  onChange({ ...values, [name]: next });
                }}
              />
              Required without default
            </label>
          )}
          <button
            disabled={disabled}
            onClick={() => {
              const next = { ...values };
              delete next[name];
              onChange(next);
            }}
          >
            Remove {name}
          </button>
        </div>
      ))}
      <label>
        New {globals ? "global variable" : "input"} name
        <input
          disabled={disabled}
          value={newName}
          placeholder="e.g. attempts"
          onChange={(e) => setNewName(e.target.value)}
        />
      </label>
      {error && <small className="error">{error}</small>}
      <button
        disabled={disabled || !newName.trim()}
        onClick={() => {
          const name = newName.trim();
          if (!/^[a-zA-Z_][a-zA-Z0-9_-]*$/.test(name) || values[name]) {
            setError(
              "Use a unique name containing letters, digits, underscores or hyphens.",
            );
            return;
          }
          onChange({ ...values, [name]: { type: "string", [key]: "" } });
          setNewName("");
          setError("");
        }}
      >
        Add {globals ? "global variable" : "input"}
      </button>
    </div>
  );
}
