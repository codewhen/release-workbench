import { useState } from "react";
import type { RunState } from "../shared/types";
import { Choice } from "../components/Choice";
import { Dialog } from "../components/Dialog";
export function ManualDialog({
  path,
  request,
  disabled,
  onClose,
  onSubmit,
}: {
  path: string;
  request: RunState["manual"][string];
  disabled: boolean;
  onClose: () => void;
  onSubmit: (note: string, decision?: boolean) => void;
}) {
  const [note, setNote] = useState(""),
    [decision, setDecision] = useState("");
  return (
    <Dialog title="Action required" onClose={onClose}>
      <h3>{request.name}</h3>
      <p>{request.instructions}</p>
      <small className="path">{path}</small>
      {request.mode === "decision" && (
        <label>
          Return Boolean
          <Choice
            label="Return Boolean"
            value={decision}
            onChange={setDecision}
            disabled={disabled}
            options={[
              { value: "", label: "Choose True or False…" },
              { value: "true", label: "True" },
              { value: "false", label: "False" },
            ]}
          />
        </label>
      )}
      <label>
        Evidence notes
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          disabled={disabled}
        />
      </label>
      <div className="actions">
        <button onClick={onClose}>Not now</button>
        <button
          className="primary"
          disabled={
            disabled ||
            !note.trim() ||
            (request.mode === "decision" && !decision)
          }
          onClick={() =>
            onSubmit(
              note,
              request.mode === "decision" ? decision === "true" : undefined,
            )
          }
        >
          Return result and continue
        </button>
      </div>
    </Dialog>
  );
}
