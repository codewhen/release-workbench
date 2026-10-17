import type { Workflow } from "../shared/types";
import { Declarations } from "../components/Declarations";
import { JsonInput } from "../components/JsonInput";
export function WorkflowSettings({
  workflow,
  editing,
  commit,
  openFunction,
  onNewFunction,
}: {
  workflow: Workflow;
  editing: boolean;
  commit: (workflow: Workflow) => void;
  openFunction: (id: string) => void;
  onNewFunction: () => void;
}) {
  return (
    <>
      <h2>Workflow settings</h2>
      <label>
        Name
        <input
          disabled={!editing}
          value={workflow.name}
          onChange={(e) => commit({ ...workflow, name: e.target.value })}
        />
      </label>
      <label>
        Concurrent operations
        <input
          disabled={!editing}
          type="number"
          min="1"
          max="64"
          value={workflow.concurrency ?? 4}
          onChange={(e) =>
            commit({
              ...workflow,
              concurrency: Number(e.target.value),
            })
          }
        />
      </label>
      <label>
        Workspace root
        <input
          disabled={!editing}
          value={workflow.workspace ?? "."}
          onChange={(e) => commit({ ...workflow, workspace: e.target.value })}
        />
      </label>
      <p className="muted">
        Relative to this YAML file. Operation paths stay within this workspace.
      </p>
      <details>
        <summary>Input discovery and report files</summary>
        <JsonInput
          label="Input discovery command"
          value={workflow.input_detection ?? null}
          disabled={!editing}
          multiline
          onChange={(v) => {
            const next = { ...workflow };
            if (v === null) delete next.input_detection;
            else next.input_detection = v as Workflow["input_detection"];
            commit(next);
          }}
        />
        <JsonInput
          label="Report path patterns"
          value={workflow.report_paths ?? []}
          disabled={!editing}
          multiline
          onChange={(v) => commit({ ...workflow, report_paths: v as string[] })}
        />
      </details>
      <h3>Workflow inputs</h3>
      <Declarations
        values={workflow.inputs ?? {}}
        disabled={!editing}
        onChange={(v) =>
          commit({ ...workflow, inputs: v as Workflow["inputs"] })
        }
      />
      <h3>Global variables</h3>
      <p>
        Declare each global here, choose its type and set its initial value.
        Every new run starts with these initial values; Get, Set and Update use
        the current run’s value.
      </p>
      <Declarations
        globals
        values={workflow.globals ?? {}}
        disabled={!editing}
        onChange={(v) =>
          commit({ ...workflow, globals: v as Workflow["globals"] })
        }
      />
      <h3>Functions</h3>
      {Object.entries(workflow.functions ?? {}).map(([k, f]) => (
        <button key={k} onClick={() => openFunction(k)}>
          {f.name ?? k} → {f.returns}
        </button>
      ))}
      <button disabled={!editing} onClick={onNewFunction}>
        Create function
      </button>
      <details>
        <summary>Environment and secrets</summary>
        <JsonInput
          label="Environment values"
          value={workflow.environment ?? {}}
          disabled={!editing}
          onChange={(v) =>
            commit({
              ...workflow,
              environment: v as Workflow["environment"],
            })
          }
          multiline
        />
        <JsonInput
          label="Secret environment names"
          value={workflow.secrets ?? []}
          disabled={!editing}
          onChange={(v) => commit({ ...workflow, secrets: v as string[] })}
          multiline
        />
      </details>
    </>
  );
}
