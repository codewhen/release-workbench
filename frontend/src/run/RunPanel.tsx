import type { RunState, Execution } from "../shared/types";
export function RunPanel({
  state,
  selected,
  graphId,
  overall,
  onSelect,
  onStop,
  onOverall,
}: {
  state: RunState;
  selected: string | null;
  graphId: string;
  overall: boolean;
  onSelect: (id: string, graph: string) => void;
  onStop: (path?: string) => void;
  onOverall: () => void;
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
      <button onClick={onOverall} aria-pressed={overall}>
        Overall run
      </button>
      <h2>
        {overall
          ? "Overall run"
          : (visible.at(-1)?.name ?? "Execution details")}
      </h2>
      <p
        className={
          "status " +
          (overall ? state.status : (visible.at(-1)?.status ?? "pending"))
        }
      >
        {(overall
          ? state.status
          : (visible.at(-1)?.status ?? "pending")
        ).replaceAll("_", " ")}
      </p>
      {overall && state.error && <p className="error">{state.error}</p>}
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
        <p>This card has not executed in the current run.</p>
      )}
      {visible.map((e) => (
        <ExecutionView
          key={e.path}
          execution={e}
          state={state}
          onStop={() => onStop(e.path)}
          expanded={!overall}
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
  expanded,
}: {
  expanded: boolean;
  execution: Execution;
  state: RunState;
  onStop: () => void;
}) {
  const elapsed = e.seconds ?? Math.max(0, Date.now() / 1000 - e.started);
  const progress = e.progress;
  const children = expanded
    ? Object.values(state.executions).filter((child) =>
        child.path.startsWith(e.path + "/"),
      )
    : [];
  const trail = expanded
    ? state.events
        .filter(
          (event) =>
            event.execution === e.path ||
            event.execution.startsWith(e.path + "/"),
        )
        .slice(-100)
    : [];
  const output = [e, ...children]
    .filter((child) => child.tail)
    .map(
      (child) => (child.path === e.path ? "" : child.name + ":\n") + child.tail,
    )
    .join("\n")
    .slice(-16000);
  return (
    <details
      className="execution-evidence"
      open={expanded || ["running", "manual", "failed"].includes(e.status)}
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
      {expanded && !e.outcome && (
        <p className="muted">
          The returned value will appear when this card completes.
        </p>
      )}
      {e.outcome && (
        <>
          <h3>Returned value</h3>
          <p>Type: {e.outcome.value.type}</p>
          <pre aria-label={e.name + " returned value"}>
            {e.outcome.value.type === "void"
              ? "No result (Void)"
              : JSON.stringify(e.outcome.value.value, null, 2)}
          </pre>
        </>
      )}
      {["running", "manual"].includes(e.status) && (
        <button onClick={onStop}>Stop this job</button>
      )}
      <h3>Live output</h3>
      <pre className="logs" aria-label={e.name + " live output"}>
        {expanded
          ? output || "No log output yet."
          : (e.tail ?? "No log output.")}
      </pre>
      {expanded && (
        <section aria-label={e.name + " live trail"}>
          <h3>Live trail</h3>
          {!trail.length && (
            <p className="muted">Waiting for execution events.</p>
          )}
          <ol className="execution-trail">
            {trail.map((event, index) => (
              <li key={index}>
                {typeof event.time === "string" && (
                  <time dateTime={event.time}>
                    {new Date(event.time).toLocaleTimeString()}
                  </time>
                )}{" "}
                <strong>
                  {state.executions[event.execution]?.name ?? e.name}
                </strong>
                {" · "}
                {event.kind.replaceAll("_", " ")}
                {typeof event.status === "string" ? " · " + event.status : ""}
              </li>
            ))}
          </ol>
        </section>
      )}
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
