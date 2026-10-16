import type { MouseEventHandler } from "react";
import {
  Play,
  Square,
  Pause,
  Plus,
  Undo2,
  Redo2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import type { RunState } from "../shared/types";
export type Representation = "canvas" | "list" | "yaml";
interface EditorToolbarProps {
  view: "edit" | "run";
  representation: Representation;
  state: RunState;
  editing: boolean;
  locked: boolean;
  dirty: boolean;
  canUndo: boolean;
  canRedo: boolean;
  hidden: boolean;
  actions: {
    add: MouseEventHandler<HTMLButtonElement>;
    save: (andRun: boolean) => void;
    undo: () => void;
    redo: () => void;
    arrange: () => void;
    validate: () => void;
    run: () => void;
    stop: () => void;
    pause: () => void;
    overall: () => void;
    manual: () => void;
    toggleDetails: () => void;
    representation: (view: Representation) => void;
  };
}
export function EditorToolbar({
  view,
  representation,
  state,
  editing,
  locked,
  dirty,
  canUndo,
  canRedo,
  hidden,
  actions,
}: EditorToolbarProps) {
  return (
    <div className="toolbar">
      <div className="actions">
        {view === "edit" ? (
          <>
            <button
              disabled={!editing || representation === "yaml"}
              onClick={actions.add}
            >
              <Plus size={17} />
              Add card
            </button>
            <button disabled={locked} onClick={() => actions.save(false)}>
              Save
            </button>
            <button
              className="primary"
              disabled={locked}
              onClick={() => actions.save(true)}
            >
              <Play size={17} />
              Save and run
            </button>
            <button
              aria-label="Undo"
              disabled={locked || !canUndo}
              onClick={actions.undo}
            >
              <Undo2 size={17} />
            </button>
            <button
              aria-label="Redo"
              disabled={locked || !canRedo}
              onClick={actions.redo}
            >
              <Redo2 size={17} />
            </button>
            <button disabled={!editing} onClick={actions.arrange}>
              Arrange
            </button>
            <button disabled={locked} onClick={actions.validate}>
              Validate & review
            </button>
          </>
        ) : (
          <>
            <button
              className="primary"
              disabled={locked || dirty}
              onClick={actions.run}
            >
              <Play size={17} />
              Run all
            </button>
            <button disabled={!state.busy} onClick={actions.stop}>
              <Square size={17} />
              Stop all
            </button>
            <button disabled={!state.busy} onClick={actions.pause}>
              <Pause size={17} />
              {state.paused ? "Resume scheduling" : "Pause scheduling"}
            </button>
            <button onClick={actions.overall}>Overall run</button>
            {Object.keys(state.manual).length > 0 && (
              <button className="primary" onClick={actions.manual}>
                Action required ({Object.keys(state.manual).length})
              </button>
            )}
            <span className={"status " + state.status}>{state.status}</span>
          </>
        )}
      </div>
      <div className="actions">
        <button onClick={actions.toggleDetails}>
          {hidden ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}{" "}
          {hidden ? "Show details" : "Hide details"}
        </button>
        {(["canvas", "list", "yaml"] as const).map((v) => (
          <button
            key={v}
            aria-pressed={representation === v}
            disabled={state.busy && v === "yaml"}
            onClick={() => actions.representation(v)}
          >
            {v === "canvas" ? "Flowchart" : v[0].toUpperCase() + v.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
