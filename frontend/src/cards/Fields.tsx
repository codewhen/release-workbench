import { WorkspaceLink } from "./WorkspaceLink";
import { TerminalValue } from "./TerminalValue";
import { Choice } from "../components/Choice";
import { ValueInput } from "./ValueInput";
import {
  VALUE_TYPES,
  type Card,
  type Field,
  type Workflow,
  type CardMeta,
} from "../shared/types";
export function fieldVisible(
  field: Field,
  config: Record<string, unknown>,
): boolean {
  return (
    (!field.when ||
      Object.entries(field.when).every(([k, v]) => config[k] === v)) &&
    (!field.unless ||
      !Object.entries(field.unless).every(([k, v]) => config[k] === v))
  );
}
export function FieldEditor({
  field,
  graphId,
  catalog,
  card,
  workflow,
  disabled,
  onChange,
  onOpenFunction,
  onNewFunction,
  onInvalid,
}: {
  field: Field;
  graphId: string;
  catalog: CardMeta[];
  card: Card;
  workflow: Workflow;
  disabled: boolean;
  onChange: (key: string, value: unknown) => void;
  onOpenFunction: (id: string) => void;
  onNewFunction: (returns?: string) => void;
  onInvalid?: (error: string) => void;
}) {
  if (["finish", "return"].includes(card.kind) && field.key === "value")
    return (
      <TerminalValue
        card={card}
        workflow={workflow}
        graphId={graphId}
        catalog={catalog}
        disabled={disabled}
        onChange={onChange}
        onInvalid={onInvalid}
      />
    );
  const value = card.config?.[field.key];
  const change = (v: unknown) => onChange(field.key, v);
  if (card.kind === "workspace" && field.key === "path")
    return (
      <div>
        <label>
          {field.label}
          <input
            className="nodrag"
            aria-label={field.label}
            disabled={disabled}
            value={typeof value === "string" ? value : JSON.stringify(value)}
            onChange={(event) => change(event.target.value)}
          />
        </label>
        <WorkspaceLink
          workflow={workflow}
          graphId={graphId}
          cardId={card.id}
          view="edit"
        />
      </div>
    );
  if (card.kind === "program" && field.key === "argv")
    return (
      <div>
        <ValueInput
          field={field}
          card={card}
          workflow={workflow}
          graphId={graphId}
          catalog={catalog}
          disabled={disabled}
          onChange={change}
          onInvalid={onInvalid}
        />
        <button
          className="nodrag"
          disabled={disabled}
          onClick={() =>
            change([
              { $ref: "runtime:python" },
              ...(Array.isArray(value) ? value.slice(1) : []),
            ])
          }
        >
          Use Workbench Python
        </button>
      </div>
    );
  if (field.widget === "function") {
    const options = Object.entries(workflow.functions ?? {})
      .filter(([, f]) => !field.returns || f.returns === field.returns)
      .map(([id, f]) => ({ value: id, label: f.name ?? id }));
    return (
      <div className="function-field">
        <label>
          {field.label}
          <Choice
            label={field.label}
            value={String(value ?? "")}
            disabled={disabled}
            onChange={change}
            options={[{ value: "", label: "Choose a function…" }, ...options]}
          />
        </label>
        <div className="function-actions">
          <button
            className="nodrag"
            disabled={disabled || !value}
            onClick={() => onOpenFunction(String(value))}
          >
            Open function
          </button>
          <button
            className="nodrag"
            disabled={disabled}
            onClick={() => onNewFunction(field.returns)}
          >
            Create function
          </button>
        </div>
      </div>
    );
  }
  if (
    field.widget === "select" ||
    field.widget === "type" ||
    field.widget === "global"
  ) {
    const options =
      field.widget === "type"
        ? VALUE_TYPES
        : field.widget === "global"
          ? Object.keys(workflow.globals ?? {})
          : (field.options ?? []);
    return (
      <label>
        {field.label}
        <Choice
          label={field.label}
          value={String(value ?? "")}
          disabled={disabled}
          onChange={change}
          options={[
            ...(!options.includes(String(value ?? ""))
              ? [{ value: "", label: "Choose…" }]
              : []),
            ...options.map((v) => ({
              value: v,
              label: v.replaceAll("_", " "),
            })),
          ]}
        />
      </label>
    );
  }
  if (field.widget === "json")
    return (
      <ValueInput
        field={field}
        card={card}
        graphId={graphId}
        catalog={catalog}
        workflow={workflow}
        disabled={disabled}
        onChange={change}
        onInvalid={onInvalid}
      />
    );
  if (field.widget === "boolean")
    return (
      <label className="check">
        <input
          type="checkbox"
          className="nodrag"
          checked={value === true}
          disabled={disabled}
          onChange={(e) => change(e.target.checked)}
        />
        {field.label}
      </label>
    );
  if (field.widget === "number")
    return (
      <label>
        {field.label}
        <input
          className="nodrag"
          type="number"
          aria-label={field.label}
          disabled={disabled}
          value={typeof value === "number" ? value : ""}
          onChange={(e) => {
            if (
              e.target.value !== "" &&
              Number.isFinite(Number(e.target.value))
            ) {
              onInvalid?.("");
              change(Number(e.target.value));
            } else onInvalid?.("Enter a number for " + field.label);
          }}
        />
      </label>
    );
  if (field.widget === "code" || field.widget === "textarea")
    return (
      <label>
        {field.label}
        <textarea
          className={`nodrag ${field.widget === "code" ? "code editor-code" : ""}`}
          aria-label={field.label}
          disabled={disabled}
          value={String(value ?? "")}
          onChange={(e) => change(e.target.value)}
        />
      </label>
    );
  return (
    <label>
      {field.label}
      <input
        className="nodrag"
        aria-label={field.label}
        disabled={disabled}
        value={typeof value === "string" ? value : JSON.stringify(value)}
        onChange={(e) => change(e.target.value)}
      />
    </label>
  );
}
