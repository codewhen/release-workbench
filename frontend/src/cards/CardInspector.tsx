import type { Connection } from "@xyflow/react";
import type { Card, Catalog, Workflow } from "../shared/types";
import { FieldEditor, fieldVisible } from "./Fields";
import { Connections } from "./Connections";
import { Bindings } from "./Bindings";
import { JsonInput } from "../components/JsonInput";

type FunctionEntry = [string, NonNullable<Workflow["functions"]>[string]];
interface CardInspectorProps {
  card: Card;
  workflow: Workflow;
  graphId: string;
  catalog: Catalog;
  editing: boolean;
  currentFunction?: FunctionEntry;
  onPatch: (changes: Partial<Card>) => void;
  onConfig: (key: string, value: unknown) => void;
  onOpenFunction: (id: string) => void;
  onNewFunction: (returns: string) => void;
  onOpenGlobals: () => void;
  onConnect: (connection: Connection) => void;
  onDeleteEdge: (id: string) => void;
  onDuplicate: () => void;
  onDelete: () => void;
}
export function CardInspector({
  card,
  workflow,
  graphId,
  catalog,
  editing,
  currentFunction,
  onPatch,
  onConfig,
  onOpenFunction,
  onNewFunction,
  onOpenGlobals,
  onConnect,
  onDeleteEdge,
  onDuplicate,
  onDelete,
}: CardInspectorProps) {
  return (
    <>
      <h2>{card.name}</h2>
      <label>
        Card name
        <input
          disabled={!editing}
          value={card.name}
          onChange={(e) => onPatch({ name: e.target.value })}
        />
      </label>
      {card.kind === "variable" && (
        <>
          <button disabled={!editing} onClick={onOpenGlobals}>
            Create / initialize global
          </button>
          <p className="muted">
            Declare a global’s type and initial value in Workflow settings. Get
            reads it; Set replaces it; Update changes its current value.
          </p>
        </>
      )}
      {card.kind === "finish" && currentFunction && (
        <div className="alert">
          <p>
            This is a function. Use Return to send its result back to the
            caller.
          </p>
          <button
            disabled={!editing}
            onClick={() =>
              onPatch({
                kind: "return",
                name: card.name === "Finish" ? "Return" : card.name,
                config: {
                  ...card.config,
                  returns: currentFunction[1].returns,
                },
              })
            }
          >
            Replace with Return
          </button>
        </div>
      )}
      {card.kind === "return" && currentFunction && (
        <p>
          Function result type: {currentFunction[1].returns}. This is declared
          by {currentFunction[0]}.
        </p>
      )}
      {catalog.cards
        .find((m) => m.kind === card.kind)!
        .fields.filter((f) => fieldVisible(f, card.config ?? {}))
        .map((f) => (
          <FieldEditor
            key={f.key}
            field={f}
            graphId={graphId}
            catalog={catalog.cards}
            card={card}
            workflow={workflow}
            disabled={!editing}
            onChange={(k, v) => onConfig(k, v)}
            onOpenFunction={onOpenFunction}
            onNewFunction={(returns) => onNewFunction(returns ?? "json")}
          />
        ))}
      <Connections
        meta={catalog.cards.find((c) => c.kind === card!.kind)!}
        catalog={catalog.cards}
        workflow={workflow}
        graphId={graphId}
        card={card}
        disabled={!editing}
        onConnect={onConnect}
        onDelete={onDeleteEdge}
      />
      <Bindings
        card={card}
        workflow={workflow}
        graphId={graphId}
        disabled={!editing}
        onChange={(inputs) => onPatch({ inputs })}
      />
      <details>
        <summary>Advanced execution settings</summary>
        <JsonInput
          label="Timeout, locks, retries and environment"
          value={card.settings ?? {}}
          disabled={!editing}
          multiline
          onChange={(settings) =>
            onPatch({
              settings: settings as Card["settings"],
            })
          }
        />
        <small>
          Use timeout, resources, exclusive, interactive, cwd, environment and
          retry. Retry defaults off.
        </small>
      </details>
      <div className="actions">
        <button
          disabled={!editing || card.kind === "start"}
          onClick={onDuplicate}
        >
          Duplicate
        </button>
        <button disabled={!editing || card.kind === "start"} onClick={onDelete}>
          Delete card
        </button>
      </div>
    </>
  );
}
