import { useState } from "react";
import { api } from "../shared/api";
import { Dialog } from "../components/Dialog";
import { JsonInput } from "../components/JsonInput";
import { Choice } from "../components/Choice";
import type { Workflow } from "../shared/types";
interface Candidate {
  value: unknown;
  label: string;
  automatic: boolean;
}
export function RunInputs({
  id,
  workflow,
  values,
  onChange,
  onClose,
  onRun,
}: {
  id: string;
  workflow: Workflow;
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  onClose: () => void;
  onRun: () => void;
}) {
  const [candidates, setCandidates] = useState<Record<string, Candidate[]>>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Dialog title="Run inputs" onClose={onClose}>
      {workflow.input_detection && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              const result = await api<{
                candidates: Record<string, Candidate[]>;
                warnings: string[];
              }>("detect-inputs", {}, id);
              setCandidates(result.candidates);
              setWarnings(result.warnings);
              const next = { ...values };
              for (const [key, items] of Object.entries(result.candidates))
                if (items.length === 1 && items[0].automatic)
                  next[key] = items[0].value;
              onChange(next);
            } catch (e) {
              setError(e instanceof Error ? e.message : String(e));
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Detecting inputs…" : "Auto-detect inputs"}
        </button>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {warnings.map((warning, index) => (
        <p key={index} role="status">
          {warning}
        </p>
      ))}
      {Object.entries(values).map(([key, value]) => (
        <div key={key}>
          {(candidates[key]?.length ?? 0) > 0 && (
            <label>
              Detected {key}
              <Choice
                label={"Detected " + key}
                value={String(
                  candidates[key].findIndex((item) => item.value === value),
                )}
                options={[
                  { value: "-1", label: "Choose a candidate…" },
                  ...candidates[key].map((item, index) => ({
                    value: String(index),
                    label: item.label,
                  })),
                ]}
                onChange={(index) => {
                  if (Number(index) >= 0)
                    onChange({
                      ...values,
                      [key]: candidates[key][Number(index)].value,
                    });
                }}
              />
            </label>
          )}
          {workflow.inputs?.[key]?.type === "string" ? (
            <label>
              {key}
              <input
                value={typeof value === "string" ? value : ""}
                onChange={(e) => onChange({ ...values, [key]: e.target.value })}
              />
            </label>
          ) : workflow.inputs?.[key]?.type === "number" ? (
            <label>
              {key}
              <input
                type="number"
                value={typeof value === "number" ? value : ""}
                onChange={(e) =>
                  onChange({
                    ...values,
                    [key]:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </label>
          ) : workflow.inputs?.[key]?.type === "boolean" ? (
            <label>
              {key}
              <Choice
                label={key}
                value={value === true ? "true" : value === false ? "false" : ""}
                options={[
                  { value: "", label: "Choose True or False…" },
                  { value: "true", label: "True" },
                  { value: "false", label: "False" },
                ]}
                onChange={(v) =>
                  onChange({ ...values, [key]: v === "" ? null : v === "true" })
                }
              />
            </label>
          ) : (
            <JsonInput
              label={key}
              value={value}
              onChange={(v) => onChange({ ...values, [key]: v })}
            />
          )}
          {workflow.inputs?.[key]?.description && (
            <p className="muted">{workflow.inputs[key].description}</p>
          )}
        </div>
      ))}
      <div className="actions">
        <button disabled={busy} onClick={onClose}>
          Cancel
        </button>
        <button className="primary" disabled={busy} onClick={onRun}>
          Run workflow
        </button>
      </div>
    </Dialog>
  );
}
