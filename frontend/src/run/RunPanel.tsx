import type { RunState, Execution } from "../shared/types";
export function RunPanel({
  state,
  selected,
  graphId,
  overall,
  onSelect,
  onStop,
}: {
  state: RunState;
  selected: string | null;
  graphId: string;
  overall: boolean;
  onSelect: (id: string, graph: string) => void;
  onStop: (path?: string) => void;
}) {
  const executions = Object.values(state.executions);
  const visible = overall
    ? executions
    : executions.filter((e) => e.card === selected && e.graph === graphId);
  const active = executions.filter((e) =>
    ["running", "manual"].includes(e.status),
  );
  return (
    <section className="run-panel">
      <h2>{overall ? "Overall run" : "Execution details"}</h2>
      <p className={"status " + state.status}>
        {state.status.replaceAll("_", " ")}
      </p>
      {state.error && <p className="error">{state.error}</p>}
      {overall && (
        <>
          <p>
            {
              executions.filter((e) =>
                ["passed", "recorded"].includes(e.status),
              ).length
            }{" "}
            passed · {executions.filter((e) => e.status === "failed").length}{" "}
            failed · {active.length} active
          </p>
          <h3>Active work</h3>
          {!active.length && <p className="muted">No cards are executing.</p>}
          {active.map((e) => (
            <button
              className="active-job"
              key={e.path}
              onClick={() => onSelect(e.card, e.graph)}
            >
              <span>
                {e.name}
                <small>{e.path}</small>
              </span>
              <span>{e.status}</span>
            </button>
          ))}
        </>
      )}
      {!overall && visible.length === 0 && (
        <p>Select Run all to execute the flowchart from Start.</p>
      )}
      {visible.map((e) => (
        <ExecutionView
          key={e.path}
          execution={e}
          state={state}
          onStop={() => onStop(e.path)}
        />
      ))}
      {state.run_id && (
        <p>
          <a
            href={`/reports/${state.run_id}/report.html`}
            target="_blank"
            rel="noreferrer"
          >
            Open complete HTML report
          </a>
        </p>
      )}
    </section>
  );
}
function ExecutionView({
  execution: e,
  state,
  onStop,
}: {
  execution: Execution;
  state: RunState;
  onStop: () => void;
}) {
  const elapsed = e.seconds ?? Math.max(0, Date.now() / 1000 - e.started);
  const progress = e.progress;
  return (
    <details
      className="execution-evidence"
      open={["running", "manual", "failed"].includes(e.status)}
    >
      <summary>
        <span>
          {e.name}
          <small>{e.path}</small>
        </span>
        <span className={"status " + e.status}>{e.status}</span>
      </summary>
      <p>
        Elapsed {elapsed.toFixed(1)}s
        {e.kind === "loop" || e.kind === "poll"
          ? " · condition-dependent duration"
          : ""}
      </p>
      {!progress &&
        e.expected_seconds &&
        ["running", "queued"].includes(e.status) && (
          <p>
            Estimated{" "}
            {Math.min(95, Math.round((elapsed / e.expected_seconds) * 100))}% ·
            approx. {Math.max(0, e.expected_seconds - elapsed).toFixed(0)}s
            remaining (estimate)
          </p>
        )}
      {progress && (
        <>
          <progress
            max={progress.total}
            value={progress.done}
            aria-label={e.name + " measured progress"}
          />
          <p>
            {Math.round((progress.done / progress.total) * 100)}% measured ·{" "}
            {progress.stage}
          </p>
        </>
      )}
      {e.error && <p className="error">{e.error}</p>}
      {e.outcome && (
        <>
          <h3>Returned value</h3>
          <pre>{JSON.stringify(e.outcome.value, null, 2)}</pre>
        </>
      )}
      {["running", "manual"].includes(e.status) && (
        <button onClick={onStop}>Stop this job</button>
      )}
      <h3>Live output</h3>
      <pre className="logs">{e.tail ?? "No log output."}</pre>
      {e.log && state.run_id && (
        <a
          target="_blank"
          rel="noreferrer"
          href={`/reports/${state.run_id}/${e.log}`}
        >
          Saved log
        </a>
      )}
      <p>{e.attempts.length} attempt(s)</p>
    </details>
  );
}
