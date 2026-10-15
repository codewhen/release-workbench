import { assertFormValidity } from "./components/validation";
import { configuredCard } from "./shared/cards";
import { useEffect, useRef, useState } from "react";
import { ReactFlowProvider, type Connection } from "@xyflow/react";
import {
  Play,
  Square,
  Pause,
  Plus,
  Undo2,
  Redo2,
  PanelLeftClose,
  PanelLeftOpen,
  GitBranch,
} from "lucide-react";
import { api, ApiError } from "./shared/api";
import {
  EMPTY_STATE,
  VALUE_TYPES,
  type Card,
  type Catalog,
  type RunState,
  type SavedDocument,
  type Workflow,
  type ValidationIssue,
} from "./shared/types";
import { useEditor } from "./editor/useEditor";
import {
  addCard,
  addFunction,
  arrange,
  clone,
  connect,
  duplicateCard,
  removeCard,
  orderedCards,
  ownershipDepth,
} from "./editor/model";
import { FlowCanvas } from "./editor/FlowCanvas";
import {
  ContextMenu,
  type MenuState,
  type MenuAction,
} from "./editor/ContextMenu";
import { FieldEditor, fieldVisible } from "./cards/Fields";
import { Connections } from "./cards/Connections";
import { Bindings } from "./cards/Bindings";
import { ManualDialog } from "./run/ManualDialog";
import { WorkflowSettings } from "./editor/WorkflowSettings";
import { RunPanel } from "./run/RunPanel";
import { Dialog } from "./components/Dialog";
import { Choice } from "./components/Choice";
import { JsonInput } from "./components/JsonInput";
import { Declarations } from "./components/Declarations";
export function EditorLoader({
  id,
  catalog,
  onHome,
}: {
  id: string;
  catalog: Catalog;
  onHome: () => void;
}) {
  const [record, setRecord] = useState<SavedDocument | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api<SavedDocument>("config", undefined, id)
      .then(setRecord)
      .catch((e) => setError(e.message));
  }, [id]);
  return record ? (
    <ReactFlowProvider>
      <Editor id={id} catalog={catalog} initial={record} onHome={onHome} />
    </ReactFlowProvider>
  ) : (
    <main className="loading">
      <h1>Workflow Workbench</h1>
      <p>{error || "Opening workflow…"}</p>
      <button onClick={onHome}>Home</button>
    </main>
  );
}
function Editor({
  id,
  catalog,
  initial,
  onHome,
}: {
  id: string;
  catalog: Catalog;
  initial: SavedDocument;
  onHome: () => void;
}) {
  const { workflow, commit, reset, undo, redo, canUndo, canRedo } = useEditor(
    initial.recovery?.workflow ?? initial.workflow,
  );
  const [saved, setSaved] = useState(initial),
    [state, setState] = useState<RunState>(EMPTY_STATE),
    [graphId, setGraphId] = useState("main"),
    [view, setView] = useState<"run" | "edit">(
      initial.recovery ? "edit" : "run",
    ),
    [representation, setRepresentation] = useState<"canvas" | "list" | "yaml">(
      innerWidth < 1000 ? "list" : "canvas",
    ),
    [selected, setSelected] = useState<string | null>(null),
    [overall, setOverall] = useState(true),
    [following, setFollowing] = useState(true),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(
      initial.recovery ? "Recovered your unsaved draft. Save to keep it." : "",
    ),
    [working, setWorking] = useState(false),
    [yaml, setYaml] = useState(initial.recovery?.yaml ?? initial.yaml),
    [yamlDirty, setYamlDirty] = useState(false),
    [review, setReview] = useState(""),
    [menu, setMenu] = useState<MenuState | null>(null),
    [newFunction, setNewFunction] = useState<{ returns: string } | null>(null),
    [functionName, setFunctionName] = useState("New function"),
    [settings, setSettings] = useState(false),
    [hidden, setHidden] = useState(false),
    [panelWidth, setPanelWidth] = useState(360),
    [leave, setLeave] = useState(false),
    [confirmDelete, setConfirmDelete] = useState<string | null>(null),
    [runInputs, setRunInputs] = useState<Record<string, unknown> | null>(null),
    [manualId, setManualId] = useState<string | null>(null);
  const [issues, setIssues] = useState<ValidationIssue[]>(
    initial.recovery ? [] : (initial.issues ?? []),
  );
  const [breadcrumbs, setBreadcrumbs] = useState<
    { graph: string; card: string | null; name: string }[]
  >([]);
  const seenManual = useRef(new Set<string>()),
    list = useRef<HTMLDivElement>(null),
    panel = useRef<HTMLElement>(null),
    graphRef = useRef<HTMLDivElement>(null),
    autoScroll = useRef(false);
  const graph = workflow.graphs[graphId],
    rawCard = graph.cards.find((c) => c.id === selected),
    card = rawCard
      ? configuredCard(
          rawCard,
          catalog.cards.find((m) => m.kind === rawCard.kind)!,
        )
      : undefined,
    dirty =
      yamlDirty || JSON.stringify(workflow) !== JSON.stringify(saved.workflow),
    locked = state.busy || working,
    editing = view === "edit" && !locked;
  const currentFunction = Object.entries(workflow.functions ?? {}).find(
    ([, f]) => f.graph === graphId,
  );
  const executions = Object.values(state.executions);
  const statuses: Record<string, string> = {};
  for (const e of executions)
    if (e.graph === graphId) statuses[e.card] = e.status;
  const active = [...executions]
    .sort((a, b) => b.path.length - a.path.length)
    .find((e) => ["running", "manual"].includes(e.status));
  const signature = JSON.stringify(state.manual);
  useEffect(() => {
    seenManual.current.clear();
    setManualId(null);
  }, [state.run_id]);
  useEffect(() => {
    const poll = () =>
      api<RunState>("state", undefined, id)
        .then(setState)
        .catch((e) => setError(e.message));
    void poll();
    const timer = setInterval(() => void poll(), 500);
    return () => clearInterval(timer);
  }, [id]);
  useEffect(() => {
    const next = Object.keys(state.manual).find(
      (path) => !seenManual.current.has(path),
    );
    if (next && !manualId) {
      seenManual.current.add(next);
      setManualId(next);
      setView("run");
    }
  }, [signature, manualId]);
  useEffect(() => {
    if (!following || view !== "run" || !active) return;
    setGraphId(active.graph);
    setSelected(active.card);
    if (representation === "list")
      requestAnimationFrame(() => {
        autoScroll.current = true;
        list.current
          ?.querySelector(`[data-card-id="${CSS.escape(active.card)}"]`)
          ?.scrollIntoView({ block: "nearest" });
      });
  }, [active?.path, following, view, representation]);
  useEffect(() => {
    const media = matchMedia("(max-width:700px)");
    const update = () => {
      if (media.matches) setRepresentation("list");
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  async function act<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setWorking(true);
    setError("");
    setIssues([]);
    try {
      return await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      if (e instanceof ApiError) setIssues(e.issues);
      return undefined;
    } finally {
      setWorking(false);
    }
  }
  function patchCard(id: string, changes: Partial<Card>) {
    if (!editing) return;
    const next = clone(workflow);
    next.graphs[graphId].cards = next.graphs[graphId].cards.map((c) =>
      c.id === id ? { ...c, ...changes } : c,
    );
    commit(next);
  }
  function config(id: string, key: string, value: unknown) {
    const c = graph.cards.find((c) => c.id === id)!;
    patchCard(id, { config: { ...c.config, [key]: value } });
  }
  function select(id: string) {
    setSelected(id);
    setOverall(false);
    setFollowing(false);
    setHidden(false);
    setSettings(false);
    requestAnimationFrame(() => {
      panel.current?.scrollTo({ top: 0 });
      if (innerWidth <= 700)
        panel.current?.scrollIntoView({
          block: "start",
          behavior: matchMedia("(prefers-reduced-motion:reduce)").matches
            ? "instant"
            : "smooth",
        });
    });
  }
  function inspect() {
    if (view === "run" && overall) {
      setOverall(false);
      setFollowing(false);
      if (active) {
        setSelected(active.card);
        setGraphId(active.graph);
      }
    }
  }
  function showOverall() {
    setOverall(true);
    setFollowing(true);
    setHidden(false);
    setSettings(false);
  }
  function openFunction(id: string) {
    const f = workflow.functions?.[id];
    if (!f) return;
    if (!workflow.graphs[f.graph]) {
      setError(
        "This function has no graph yet. Create it in YAML or choose Create function.",
      );
      return;
    }
    setBreadcrumbs((old) => [
      ...old,
      {
        graph: graphId,
        card: selected,
        name: currentFunction?.[1].name ?? workflow.name,
      },
    ]);
    setGraphId(f.graph);
    setSelected(null);
    setOverall(false);
    setFollowing(false);
  }
  function context(
    event: Pick<MouseEvent, "preventDefault" | "clientX" | "clientY">,
    target: {
      kind: "canvas" | "card" | "edge" | "area";
      id?: string;
      point?: { x: number; y: number };
    },
  ) {
    if (!editing) return;
    event.preventDefault();
    setMenu({ ...target, x: event.clientX, y: event.clientY });
  }
  function createCard(kind: string) {
    const meta = catalog.cards.find((c) => c.kind === kind);
    if (!meta) return;
    const next = addCard(workflow, graphId, meta, menu?.point);
    commit(next.workflow);
    setSelected(next.id);
    setOverall(false);
    setHidden(false);
    setMenu(null);
    setNotice(
      "Card added. Connect its execution ports to place it in the flowchart.",
    );
  }
  function wire(connection: Connection) {
    if (!editing || !connection.source || !connection.target) return;
    try {
      commit(
        connect(
          workflow,
          graphId,
          connection.source,
          connection.target,
          connection.sourceHandle ?? "flow:next",
          connection.targetHandle ?? "flow:entry",
        ),
      );
      setError("");
      setNotice("Connection added. Validate the flowchart before running.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function changeArea(
    id: string,
    changes: { width?: number; height?: number; collapsed?: boolean },
  ) {
    const next = clone(workflow);
    Object.assign(
      next.layout![graphId].areas!.find((a) => a.id === id)!,
      changes,
    );
    commit(next);
  }
  function move(id: string, position: { x: number; y: number }) {
    if (!editing) return;
    const next = clone(workflow);
    next.layout ??= {};
    next.layout[graphId] ??= { positions: {}, areas: [] };
    next.layout[graphId].positions ??= {};
    const area = next.layout[graphId].areas?.find((a) => a.id === id);
    if (area) {
      const dx = position.x - area.position.x,
        dy = position.y - area.position.y;
      for (const member of area.members ?? []) {
        const p = next.layout[graphId].positions![member];
        if (p)
          next.layout[graphId].positions![member] = {
            x: p.x + dx,
            y: p.y + dy,
          };
      }
      area.position = position;
    } else next.layout[graphId].positions![id] = position;
    commit(next);
  }
  async function checked() {
    assertFormValidity();
    return api<{ workflow: Workflow; yaml: string; diff: string }>(
      "validate",
      yamlDirty ? { yaml } : { workflow },
      id,
    );
  }
  async function validate() {
    await act(async () => {
      const result = await checked();
      if (yamlDirty) commit(result.workflow);
      setYaml(result.yaml);
      setYamlDirty(false);
      setReview(result.diff || "Workflow is valid. No configuration changes.");
      setNotice("Validation passed.");
    });
  }
  async function save(andRun = false) {
    await act(async () => {
      assertFormValidity();
      const record = await api<SavedDocument>(
        "save",
        { ...(yamlDirty ? { yaml } : { workflow }), revision: saved.revision },
        id,
      );
      setSaved(record);
      reset(record.workflow);
      setYaml(record.yaml);
      setYamlDirty(false);
      setNotice(
        record.runnable === false
          ? `Draft saved. ${record.validation_errors?.length ?? 0} validation issue(s) must be fixed before running.`
          : "Workflow saved.",
      );
      setIssues(record.issues ?? []);
      setReview("");
      if (andRun && record.runnable !== false) prepareRun(record);
      else if (andRun)
        setError(
          "Draft saved. Complete the execution connections before running.",
        );
    });
  }
  function prepareRun(record = saved) {
    const values = Object.fromEntries(
      Object.entries(record.workflow.inputs ?? {}).map(([k, v]) => [
        k,
        v.default ?? null,
      ]),
    );
    if (Object.keys(values).length) {
      setRunInputs(values);
      return;
    }
    void start(record, {});
  }
  async function start(record: SavedDocument, inputs: Record<string, unknown>) {
    await act(async () => {
      assertFormValidity();
      setState(
        await api<RunState>("run", { revision: record.revision, inputs }, id),
      );
      setView("run");
      showOverall();
      setRunInputs(null);
    });
  }
  async function mode(next: "canvas" | "list" | "yaml") {
    if (yamlDirty && next !== "yaml") {
      const result = await act(() =>
        api<{ workflow: Workflow; yaml: string; diff: string }>(
          "draft",
          { yaml },
          id,
        ),
      );
      if (!result) return;
      commit(result.workflow);
      setYaml(result.yaml);
      setYamlDirty(false);
    }
    if (next === "yaml" && !yamlDirty)
      setYaml(
        (await act(() => api<{ yaml: string }>("draft", { workflow }, id)))
          ?.yaml ?? yaml,
      );
    setRepresentation(next);
  }
  const addItems: MenuAction[] = [
    ...["area", "collapsible", "annotation"].map((kind) => ({
      id: "layout:" + kind,
      label:
        kind === "area"
          ? "Dotted area"
          : kind === "collapsible"
            ? "Collapsible area"
            : "Annotation",
      category: "Layout",
    })),
    ...catalog.cards
      .filter((c) => c.kind !== "start")
      .map((c) => ({ id: c.kind, label: c.label, category: c.category })),
  ];
  function chooseMenu(action: string) {
    if (action.startsWith("layout:")) {
      const next = clone(workflow);
      next.layout ??= {};
      next.layout[graphId] ??= { positions: {}, areas: [] };
      next.layout[graphId].areas ??= [];
      const areaId = "area-" + Date.now();
      next.layout[graphId].areas!.push({
        id: areaId,
        kind: action.slice(7) as "area" | "collapsible" | "annotation",
        name: "Organize this area",
        position: menu?.point ?? { x: 0, y: 0 },
        width: 600,
        height: 300,
        members: [],
      });
      commit(next);
      setSelected(areaId);
    } else if (action === "delete") {
      if (menu?.kind === "edge") {
        const next = clone(workflow);
        next.graphs[graphId].edges = graph.edges.filter(
          (e) => e.id !== menu.id,
        );
        commit(next);
      } else setConfirmDelete(menu?.id ?? null);
    } else if (action === "duplicate" && menu?.id) {
      const next = duplicateCard(workflow, graphId, menu.id);
      commit(next.workflow);
      setSelected(next.id);
    } else if (action === "disconnect" && menu?.id) {
      const next = clone(workflow);
      next.graphs[graphId].edges = graph.edges.filter(
        (e) => e.source !== menu.id && e.target !== menu.id,
      );
      commit(next);
    } else createCard(action);
    setMenu(null);
  }
  const area = workflow.layout?.[graphId]?.areas?.find(
    (a) => a.id === selected,
  );
  const currentManual = manualId ? state.manual[manualId] : undefined;
  return (
    <div className="workbench">
      <header>
        <div className="brand">
          <GitBranch size={26} />
          <div>
            <h1>Workflow Workbench</h1>
            <p>
              {workflow.name} ·{" "}
              {dirty
                ? "Unsaved draft"
                : saved.runnable === false
                  ? "Saved draft · not ready to run"
                  : "Saved configuration"}
            </p>
          </div>
        </div>
        <div className="actions">
          <button onClick={() => (dirty ? setLeave(true) : onHome())}>
            Home
          </button>
          <button
            aria-pressed={settings}
            onClick={() => {
              setSettings(!settings);
              setOverall(false);
              setHidden(false);
            }}
          >
            Workflow settings
          </button>
          <button
            aria-pressed={view === "edit"}
            disabled={locked}
            onClick={() => setView("edit")}
          >
            Edit
          </button>
          <button aria-pressed={view === "run"} onClick={() => setView("run")}>
            Run
          </button>
        </div>
      </header>
      {error && (
        <div className="alert error" role="alert">
          <span>{error}</span>
          <button onClick={() => setError("")}>Dismiss error</button>
        </div>
      )}
      {notice && (
        <div className="alert" role="status">
          <span>{notice}</span>
          <button onClick={() => setNotice("")}>Dismiss</button>
        </div>
      )}
      {issues.length > 0 && (
        <div className="validation-issues" aria-label="Workflow issues">
          {issues.map((issue) => (
            <button
              key={issue.graph + ":" + issue.card + ":" + issue.port}
              onClick={() => {
                setGraphId(issue.graph);
                setView("edit");
                setSettings(false);
                select(issue.card);
                setRepresentation("list");
                requestAnimationFrame(() =>
                  panel.current
                    ?.querySelector<HTMLButtonElement>(
                      '[aria-label="Connect to card"]',
                    )
                    ?.focus(),
                );
              }}
            >
              Connect{" "}
              {workflow.graphs[issue.graph]?.cards.find(
                (c) => c.id === issue.card,
              )?.name ?? issue.card}
              .{issue.port}
            </button>
          ))}
        </div>
      )}
      <div className="toolbar">
        <div className="actions">
          {view === "edit" ? (
            <>
              <button
                disabled={!editing || representation === "yaml"}
                onClick={(e) =>
                  setMenu({ kind: "canvas", x: e.clientX, y: e.clientY })
                }
              >
                <Plus size={17} />
                Add card
              </button>
              <button disabled={locked} onClick={() => void save()}>
                Save
              </button>
              <button
                className="primary"
                disabled={locked}
                onClick={() => void save(true)}
              >
                <Play size={17} />
                Save and run
              </button>
              <button
                aria-label="Undo"
                disabled={locked || !canUndo}
                onClick={undo}
              >
                <Undo2 size={17} />
              </button>
              <button
                aria-label="Redo"
                disabled={locked || !canRedo}
                onClick={redo}
              >
                <Redo2 size={17} />
              </button>
              <button
                disabled={!editing}
                onClick={() => commit(arrange(workflow, graphId))}
              >
                Arrange
              </button>
              <button disabled={locked} onClick={() => void validate()}>
                Validate & review
              </button>
            </>
          ) : (
            <>
              <button
                className="primary"
                disabled={locked || dirty}
                onClick={() => prepareRun()}
              >
                <Play size={17} />
                Run all
              </button>
              <button
                disabled={!state.busy}
                onClick={() => void act(() => api("stop", {}, id))}
              >
                <Square size={17} />
                Stop all
              </button>
              <button
                disabled={!state.busy}
                onClick={() =>
                  void act(() => api("pause", { paused: !state.paused }, id))
                }
              >
                <Pause size={17} />
                {state.paused ? "Resume scheduling" : "Pause scheduling"}
              </button>
              <button onClick={showOverall}>Overall run</button>
              {Object.keys(state.manual).length > 0 && (
                <button
                  className="primary"
                  onClick={() => setManualId(Object.keys(state.manual)[0])}
                >
                  Action required ({Object.keys(state.manual).length})
                </button>
              )}
              <span className={"status " + state.status}>{state.status}</span>
            </>
          )}
        </div>
        <div className="actions">
          <button onClick={() => setHidden(!hidden)}>
            {hidden ? (
              <PanelLeftOpen size={17} />
            ) : (
              <PanelLeftClose size={17} />
            )}{" "}
            {hidden ? "Show details" : "Hide details"}
          </button>
          {(["canvas", "list", "yaml"] as const).map((v) => (
            <button
              key={v}
              aria-pressed={representation === v}
              disabled={state.busy && v === "yaml"}
              onClick={() => void mode(v)}
            >
              {v === "canvas" ? "Flowchart" : v[0].toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <nav className="breadcrumbs" aria-label="Function navigation">
        <button
          onClick={() => {
            setGraphId("main");
            setBreadcrumbs([]);
            setSelected(null);
          }}
        >
          {workflow.name}
        </button>
        {breadcrumbs
          .filter((b) => b.graph !== "main")
          .map((b, i) => (
            <button
              key={i}
              onClick={() => {
                setGraphId(b.graph);
                setSelected(b.card);
                setBreadcrumbs(breadcrumbs.slice(0, i));
              }}
            >
              {b.name}
            </button>
          ))}
        {currentFunction && (
          <>
            <span>
              / {currentFunction[1].name ?? currentFunction[0]} · returns{" "}
              {currentFunction[1].returns}
            </span>
            <button
              onClick={() => {
                const b = breadcrumbs.at(-1);
                setGraphId(b?.graph ?? "main");
                setSelected(b?.card ?? null);
                setBreadcrumbs((old) => old.slice(0, -1));
              }}
            >
              Back to caller
            </button>
          </>
        )}
      </nav>
      <div
        className={`workspace ${hidden ? "panel-hidden" : ""}`}
        style={{ "--panel-width": panelWidth + "px" } as React.CSSProperties}
      >
        {!hidden && (
          <>
            <aside
              ref={panel}
              aria-label={
                overall && view === "run" ? "Overall run" : "Card settings"
              }
            >
              {settings ? (
                <WorkflowSettings
                  workflow={workflow}
                  editing={editing}
                  commit={commit}
                  openFunction={openFunction}
                  onNewFunction={() => setNewFunction({ returns: "void" })}
                />
              ) : view === "run" ? (
                <RunPanel
                  state={state}
                  selected={selected}
                  graphId={graphId}
                  overall={overall}
                  onSelect={(id, g) => {
                    setGraphId(g);
                    select(id);
                  }}
                  onStop={(path) =>
                    void act(() => api("stop", { execution: path }, id))
                  }
                />
              ) : area ? (
                <>
                  <h2>Layout area</h2>
                  <p>
                    Only canvas arrangement changes. Execution and scope stay
                    the same.
                  </p>
                  <label>
                    Name
                    <input
                      value={area.name}
                      onChange={(e) => {
                        const next = clone(workflow);
                        const target = next.layout![graphId].areas!.find(
                          (a) => a.id === area.id,
                        )!;
                        target.name = e.target.value;
                        commit(next);
                      }}
                    />
                  </label>
                  <fieldset>
                    <legend>Cards in this layout area</legend>
                    {graph.cards.map((c) => (
                      <label className="check" key={c.id}>
                        <input
                          type="checkbox"
                          checked={area.members?.includes(c.id) ?? false}
                          onChange={(e) => {
                            const next = clone(workflow);
                            const target = next.layout![graphId].areas!.find(
                              (a) => a.id === area.id,
                            )!;
                            target.members = e.target.checked
                              ? [...(target.members ?? []), c.id]
                              : (target.members ?? []).filter(
                                  (id) => id !== c.id,
                                );
                            commit(next);
                          }}
                        />
                        {c.name}
                      </label>
                    ))}
                  </fieldset>
                </>
              ) : card ? (
                <>
                  <h2>{card.name}</h2>
                  <label>
                    Card name
                    <input
                      disabled={!editing}
                      value={card.name}
                      onChange={(e) =>
                        patchCard(card.id, { name: e.target.value })
                      }
                    />
                  </label>
                  {catalog.cards
                    .find((m) => m.kind === card.kind)!
                    .fields.filter((f) => fieldVisible(f, card.config ?? {}))
                    .map((f) => (
                      <FieldEditor
                        key={f.key}
                        field={f}
                        card={card}
                        workflow={workflow}
                        disabled={!editing}
                        onChange={(k, v) => config(card.id, k, v)}
                        onOpenFunction={openFunction}
                        onNewFunction={(returns) =>
                          setNewFunction({ returns: returns ?? "json" })
                        }
                      />
                    ))}
                  <Connections
                    meta={catalog.cards.find((c) => c.kind === card!.kind)!}
                    catalog={catalog.cards}
                    workflow={workflow}
                    graphId={graphId}
                    card={card}
                    disabled={!editing}
                    onConnect={wire}
                    onDelete={(edge) => {
                      const next = clone(workflow);
                      next.graphs[graphId].edges = graph.edges.filter(
                        (e) => e.id !== edge,
                      );
                      commit(next);
                    }}
                  />
                  <Bindings
                    card={card}
                    workflow={workflow}
                    graphId={graphId}
                    disabled={!editing}
                    onChange={(inputs) => patchCard(card.id, { inputs })}
                  />
                  <details>
                    <summary>Advanced execution settings</summary>
                    <JsonInput
                      label="Timeout, locks, retries and environment"
                      value={card.settings ?? {}}
                      disabled={!editing}
                      multiline
                      onChange={(settings) =>
                        patchCard(card.id, {
                          settings: settings as Card["settings"],
                        })
                      }
                    />
                    <small>
                      Use timeout, resources, exclusive, interactive, cwd,
                      environment and retry. Retry defaults off.
                    </small>
                  </details>
                  <div className="actions">
                    <button
                      disabled={!editing || card.kind === "start"}
                      onClick={() => {
                        const next = duplicateCard(workflow, graphId, card.id);
                        commit(next.workflow);
                        setSelected(next.id);
                      }}
                    >
                      Duplicate
                    </button>
                    <button
                      disabled={!editing || card.kind === "start"}
                      onClick={() => setConfirmDelete(card.id)}
                    >
                      Delete card
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <h2>
                    {currentFunction
                      ? "Function flowchart"
                      : "Build your flowchart"}
                  </h2>
                  {currentFunction && (
                    <>
                      <p>
                        Returns {currentFunction[1].returns}. Every successful
                        path must reach Return.
                      </p>
                      <h3>Function inputs</h3>
                      <Declarations
                        values={currentFunction[1].inputs ?? {}}
                        disabled={!editing}
                        onChange={(v) => {
                          const next = clone(workflow);
                          next.functions![currentFunction[0]].inputs =
                            v as NonNullable<
                              Workflow["functions"]
                            >[string]["inputs"];
                          commit(next);
                        }}
                      />
                    </>
                  )}
                  <p>
                    Select a card to configure it, or right-click the canvas to
                    add one. Round ports run cards; square ports carry values.
                  </p>
                </>
              )}
            </aside>
            <div
              className="resize-panel"
              role="separator"
              aria-label="Resize details panel"
              aria-orientation="vertical"
              tabIndex={0}
              onKeyDown={(e) => {
                if (["ArrowLeft", "ArrowRight"].includes(e.key))
                  setPanelWidth((w) =>
                    Math.max(
                      280,
                      Math.min(650, w + (e.key === "ArrowRight" ? 20 : -20)),
                    ),
                  );
              }}
              onPointerDown={(e) => {
                e.currentTarget.setPointerCapture(e.pointerId);
                const start = e.clientX,
                  width = panelWidth;
                const target = e.currentTarget;
                const move = (event: PointerEvent) =>
                  setPanelWidth(
                    Math.max(
                      280,
                      Math.min(
                        650,
                        innerWidth - 350,
                        width + event.clientX - start,
                      ),
                    ),
                  );
                const stop = () => {
                  target.removeEventListener("pointermove", move);
                  target.removeEventListener("pointerup", stop);
                };
                target.addEventListener("pointermove", move);
                target.addEventListener("pointerup", stop);
              }}
            />
          </>
        )}
        <div className={"graph " + representation} ref={graphRef}>
          {representation === "canvas" ? (
            <FlowCanvas
              workflow={workflow}
              graphId={graphId}
              catalog={catalog.cards}
              editing={editing}
              selected={selected}
              statuses={statuses}
              focus={
                view === "edit"
                  ? selected
                  : following && active?.graph === graphId
                    ? active.card
                    : null
              }
              following={view === "edit" || following}
              onInspect={inspect}
              onSelect={select}
              onConnect={wire}
              onMove={move}
              onArea={changeArea}
              onMenu={context}
              onConfig={config}
              onOpenFunction={openFunction}
              onNewFunction={(returns) =>
                setNewFunction({ returns: returns ?? "json" })
              }
              onDetails={select}
            />
          ) : representation === "list" ? (
            <div
              className="card-list"
              ref={list}
              role="region"
              aria-label="Flowchart cards"
              tabIndex={0}
              onScroll={() => {
                if (autoScroll.current) {
                  autoScroll.current = false;
                  return;
                }
                inspect();
              }}
            >
              <h2>{currentFunction?.[1].name ?? "Workflow cards"}</h2>
              {orderedCards(graph).map((c) => (
                <button
                  key={c.id}
                  data-card-id={c.id}
                  style={{
                    marginLeft: ownershipDepth(graph, c) * 14,
                    flexShrink: 0,
                  }}
                  className={`list-card state-${statuses[c.id] ?? "pending"}`}
                  aria-pressed={selected === c.id}
                  aria-current={
                    statuses[c.id] === "running" ? "step" : undefined
                  }
                  onClick={() => select(c.id)}
                  onContextMenu={(e) => context(e, { kind: "card", id: c.id })}
                  onKeyDown={(e) => {
                    if (e.shiftKey && e.key === "F10") {
                      e.preventDefault();
                      setMenu({ kind: "card", id: c.id, x: 100, y: 200 });
                    }
                  }}
                >
                  <strong>{c.name}</strong>
                  <span>
                    {catalog.cards.find((m) => m.kind === c.kind)?.label} ·{" "}
                    {statuses[c.id] ?? "pending"}
                  </span>
                  {c.owner && (
                    <small>
                      {c.owner.card} / {c.owner.region}
                    </small>
                  )}
                </button>
              ))}
              {editing && (
                <button
                  onClick={(e) =>
                    setMenu({ kind: "canvas", x: e.clientX, y: e.clientY })
                  }
                >
                  Add card
                </button>
              )}
            </div>
          ) : (
            <div className="yaml-editor">
              <h2>Workflow YAML</h2>
              <p>One schema powers the flowchart, forms and CLI.</p>
              <textarea
                aria-label="Workflow YAML"
                className="code"
                disabled={locked}
                value={yaml}
                onChange={(e) => {
                  setYaml(e.target.value);
                  setYamlDirty(true);
                }}
              />
              <button disabled={locked} onClick={() => void validate()}>
                Validate and apply YAML
              </button>
            </div>
          )}
        </div>
      </div>
      {review && (
        <Dialog
          title="Validation and configuration changes"
          onClose={() => setReview("")}
        >
          <pre>{review}</pre>
          <button onClick={() => setReview("")}>Close review</button>
        </Dialog>
      )}
      {menu && (
        <ContextMenu
          menu={menu}
          items={
            menu.kind === "canvas"
              ? addItems
              : menu.kind === "edge"
                ? [{ id: "delete", label: "Delete connection" }]
                : menu.kind === "area"
                  ? [{ id: "delete", label: "Remove layout area" }]
                  : graph.cards.find((c) => c.id === menu.id)?.kind === "start"
                    ? [{ id: "disconnect", label: "Disconnect all" }]
                    : [
                        { id: "duplicate", label: "Duplicate card" },
                        { id: "disconnect", label: "Disconnect all" },
                        { id: "delete", label: "Delete card" },
                      ]
          }
          onChoose={chooseMenu}
          onClose={() => setMenu(null)}
        />
      )}
      {newFunction && (
        <Dialog title="Create function" onClose={() => setNewFunction(null)}>
          <label>
            Function name
            <input
              value={functionName}
              onChange={(e) => setFunctionName(e.target.value)}
            />
          </label>
          <label>
            Returns
            <Choice
              label="Function return type"
              value={newFunction.returns}
              disabled={newFunction.returns === "boolean"}
              onChange={(returns) => setNewFunction({ returns })}
              options={VALUE_TYPES.map((value) => ({ value, label: value }))}
            />
          </label>
          <div className="actions">
            <button onClick={() => setNewFunction(null)}>Cancel</button>
            <button
              className="primary"
              onClick={() => {
                const next = addFunction(
                  workflow,
                  functionName,
                  newFunction.returns,
                );
                if (card && ["if", "loop", "call", "poll"].includes(card.kind))
                  next.workflow.graphs[graphId].cards.find(
                    (c) => c.id === card.id,
                  )!.config = { ...card.config, function: next.id };
                commit(next.workflow);
                const f = next.workflow.functions![next.id];
                setBreadcrumbs((old) => [
                  ...old,
                  {
                    graph: graphId,
                    card: selected,
                    name: currentFunction?.[1].name ?? workflow.name,
                  },
                ]);
                setGraphId(f.graph);
                setSelected(null);
                setNewFunction(null);
              }}
            >
              Create and open
            </button>
          </div>
        </Dialog>
      )}
      {runInputs && (
        <Dialog title="Run inputs" onClose={() => setRunInputs(null)}>
          {Object.entries(runInputs).map(([key, value]) => (
            <JsonInput
              key={key}
              label={key}
              value={value}
              onChange={(v) => setRunInputs({ ...runInputs, [key]: v })}
            />
          ))}
          <div className="actions">
            <button onClick={() => setRunInputs(null)}>Cancel</button>
            <button
              className="primary"
              onClick={() => void start(saved, runInputs)}
            >
              Run workflow
            </button>
          </div>
        </Dialog>
      )}
      {currentManual && manualId && (
        <ManualDialog
          key={manualId}
          path={manualId}
          request={currentManual}
          disabled={working}
          onClose={() => setManualId(null)}
          onSubmit={(note, decision) =>
            void act(async () => {
              setState(
                await api<RunState>(
                  "record",
                  { execution: manualId, note, decision },
                  id,
                ),
              );
              setManualId(null);
            })
          }
        />
      )}
      {leave && (
        <Dialog title="Leave unsaved changes?" onClose={() => setLeave(false)}>
          <p>
            Your saved configuration and reports stay available. This browser
            draft will be discarded.
          </p>
          <button onClick={() => setLeave(false)}>Keep editing</button>
          <button onClick={onHome}>Discard draft and go Home</button>
        </Dialog>
      )}
      {confirmDelete && (
        <Dialog title="Delete card?" onClose={() => setConfirmDelete(null)}>
          <p>
            Its owned Body/Catch/Finally branches will also be removed. Undo
            restores this change.
          </p>
          <button onClick={() => setConfirmDelete(null)}>Cancel</button>
          <button
            onClick={() => {
              try {
                if (
                  workflow.layout?.[graphId]?.areas?.some(
                    (a) => a.id === confirmDelete,
                  )
                ) {
                  const next = clone(workflow);
                  next.layout![graphId].areas = next.layout![
                    graphId
                  ].areas!.filter((a) => a.id !== confirmDelete);
                  commit(next);
                } else commit(removeCard(workflow, graphId, confirmDelete));
                setConfirmDelete(null);
                setSelected(null);
              } catch (e) {
                setError((e as Error).message);
                setConfirmDelete(null);
              }
            }}
          >
            Delete card
          </button>
        </Dialog>
      )}
      <footer>
        Local automation ·{" "}
        {currentFunction ? "Function scope" : "Workflow scope"} · Execution
        connections run cards; value connections supply data.
      </footer>
    </div>
  );
}
