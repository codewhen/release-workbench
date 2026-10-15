import { useEffect, useRef, useState } from "react";
import { Folder, FolderPlus, Plus, Upload, GitBranch } from "lucide-react";
import { api } from "./shared/api";
import type { Catalog, Library, LibraryEntry } from "./shared/types";
import { Choice } from "./components/Choice";
import { Dialog } from "./components/Dialog";
import { ContextMenu, type MenuState } from "./editor/ContextMenu";
export function Home({
  catalog,
  onOpen,
}: {
  catalog: Catalog;
  onOpen: (id: string) => void;
}) {
  const [library, setLibrary] = useState<Library>({
      projects: [],
      folders: [],
      entries: [],
    }),
    [error, setError] = useState(""),
    [query, setQuery] = useState(""),
    [folder, setFolder] = useState("*"),
    [project, setProject] = useState("*"),
    [create, setCreate] = useState(false),
    [register, setRegister] = useState(false),
    [path, setPath] = useState(""),
    [name, setName] = useState("My workflow"),
    [filename, setFilename] = useState("workflow-workbench.yaml"),
    [template, setTemplate] = useState("blank"),
    [newProject, setNewProject] = useState(""),
    [menu, setMenu] = useState<MenuState | null>(null),
    [organize, setOrganize] = useState<{
      action: string;
      id?: string;
      old?: string;
    } | null>(null),
    [folderName, setFolderName] = useState(""),
    [importFile, setImportFile] = useState<{
      filename: string;
      yaml: string;
    } | null>(null),
    [working, setWorking] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const [history, setHistory] = useState<
    { run_id: string; name: string; status: string }[]
  >([]);
  useEffect(() => {
    api<typeof history>("history")
      .then(setHistory)
      .catch(() => {});
  }, []);
  const load = () =>
    api<Library>("library")
      .then((value) => {
        setLibrary(value);
        setNewProject((old) => old || value.projects[0] || "");
      })
      .catch((e) => setError(String(e.message)));
  useEffect(() => {
    void load();
  }, []);
  async function act(task: () => Promise<void>) {
    setWorking(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setWorking(false);
    }
  }
  const entries = library.entries.filter(
    (e) =>
      (folder === "*" || e.folder === folder) &&
      (project === "*" || e.path.startsWith(project + "/")) &&
      (e.name + " " + e.path).toLowerCase().includes(query.toLowerCase()),
  );
  const context = (
    event: React.MouseEvent,
    kind: "card" | "area",
    id: string,
  ) => {
    event.preventDefault();
    setMenu({ kind, id, x: event.clientX, y: event.clientY });
  };
  return (
    <main className="home">
      <header className="home-header">
        <div className="brand">
          <GitBranch size={28} />
          <div>
            <h1>Workflow Workbench</h1>
            <p>Build a flowchart. Automate the work.</p>
          </div>
        </div>
        <span className="preview-badge">New architecture preview</span>
      </header>
      <div className="home-title">
        <div>
          <h2>Your workflows</h2>
          <p>
            Local automation across your projects. Opening a workflow does not
            run it.
          </p>
        </div>
        <div className="actions">
          <button onClick={() => input.current?.click()}>
            <Upload size={17} />
            Open YAML
          </button>
          <button onClick={() => setRegister(!register)}>
            Add project or file
          </button>
          <button className="primary" onClick={() => setCreate(!create)}>
            <Plus size={17} />
            New workflow
          </button>
        </div>
      </div>
      <input
        ref={input}
        type="file"
        accept=".yaml,.yml"
        hidden
        aria-label="Workflow YAML file"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file)
            void file
              .text()
              .then((yaml) => setImportFile({ filename: file.name, yaml }));
          e.currentTarget.value = "";
        }}
      />
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
      {register && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              const result = await api<LibraryEntry | Library>("register", {
                path,
              });
              if ("id" in result) onOpen(result.id);
              else setLibrary(result);
              setRegister(false);
            });
          }}
        >
          <h3>Add an existing project or workflow</h3>
          <label>
            Absolute folder or YAML path
            <input
              value={path}
              onChange={(e) => setPath(e.target.value)}
              required
            />
          </label>
          <button disabled={working} className="primary">
            Add to library
          </button>
        </form>
      )}
      {create && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void act(async () => {
              const entry = await api<LibraryEntry>("create", {
                name,
                filename,
                project: newProject,
                template,
              });
              onOpen(entry.id);
            });
          }}
        >
          <h3>New workflow</h3>
          <div className="form-grid">
            <label>
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label>
              Filename
              <input
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                required
              />
            </label>
            <label>
              Project folder
              <input
                value={newProject}
                onChange={(e) => setNewProject(e.target.value)}
                required
              />
            </label>
            <label>
              Starter
              <Choice
                label="Starter"
                value={template}
                onChange={setTemplate}
                options={Object.entries(catalog.templates).map(
                  ([value, label]) => ({ value, label }),
                )}
              />
            </label>
          </div>
          <button disabled={working} className="primary">
            Create workflow
          </button>
        </form>
      )}
      <div className="library-layout">
        <nav aria-label="Workflow folders">
          <h3>Folders</h3>
          <button
            onClick={() => {
              setFolderName("");
              setOrganize({ action: "new_folder" });
            }}
          >
            <FolderPlus size={17} />
            New folder
          </button>
          {[
            { id: "*", name: "All workflows" },
            { id: "", name: "Unfiled" },
            ...library.folders.map((id) => ({ id, name: id })),
          ].map((f) => (
            <button
              className="folder-button"
              aria-pressed={folder === f.id}
              key={f.id}
              onClick={() => setFolder(f.id)}
              onContextMenu={(e) => {
                if (f.id && f.id !== "*") context(e, "area", f.id);
              }}
              onKeyDown={(e) => {
                if (e.shiftKey && e.key === "F10" && f.id && f.id !== "*") {
                  e.preventDefault();
                  setMenu({ kind: "area", id: f.id, x: 24, y: 300 });
                }
              }}
            >
              <Folder size={16} />
              {f.name}
            </button>
          ))}
        </nav>
        <section>
          <div className="library-filter">
            <label>
              Find a workflow
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <label>
              Project
              <Choice
                label="Project"
                value={project}
                onChange={setProject}
                options={[
                  { value: "*", label: "All projects" },
                  ...library.projects.map((value) => ({ value, label: value })),
                ]}
              />
            </label>
            <button onClick={() => void load()}>Refresh</button>
          </div>
          {!entries.length && (
            <div className="empty">
              <h3>No workflows here yet</h3>
              <p>Create a blank flowchart or start from a working example.</p>
              <button onClick={() => setCreate(true)}>Create a workflow</button>
            </div>
          )}
          {entries.map((entry) => (
            <article
              className="workflow-row"
              key={entry.id}
              onContextMenu={(e) => context(e, "card", entry.id)}
            >
              <div>
                <h3>{entry.name}</h3>
                <p className="path">{entry.path}</p>
                <small>{entry.error ?? (entry.folder || "Unfiled")}</small>
              </div>
              <button
                disabled={!entry.supported}
                onClick={() => onOpen(entry.id)}
              >
                Open workflow
              </button>
            </article>
          ))}
        </section>
      </div>
      {importFile && (
        <Dialog title="Open YAML workflow" onClose={() => setImportFile(null)}>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <p>
            The browser supplies the file contents. Choose the project where
            this preview should save and execute it. Existing files are never
            overwritten.
          </p>
          <label>
            Filename
            <input
              value={importFile.filename}
              onChange={(e) =>
                setImportFile({ ...importFile, filename: e.target.value })
              }
            />
          </label>
          <label>
            Project folder
            <input
              value={newProject}
              onChange={(e) => setNewProject(e.target.value)}
            />
          </label>
          <div className="actions">
            <button onClick={() => setImportFile(null)}>Cancel</button>
            <button
              className="primary"
              disabled={working}
              onClick={() =>
                void act(async () => {
                  const entry = await api<LibraryEntry>("import", {
                    ...importFile,
                    project: newProject,
                  });
                  onOpen(entry.id);
                })
              }
            >
              Validate and open
            </button>
          </div>
        </Dialog>
      )}
      {menu && (
        <ContextMenu
          menu={menu}
          items={
            menu.kind === "area"
              ? [
                  { id: "rename_folder", label: "Rename folder" },
                  {
                    id: "remove_folder",
                    label: "Remove folder",
                    description: "Keep its workflows in Unfiled",
                  },
                ]
              : [{ id: "move", label: "Move to folder" }]
          }
          onClose={() => setMenu(null)}
          onChoose={(action) => {
            setOrganize({ action, id: menu.id, old: menu.id });
            setFolderName(action === "rename_folder" ? (menu.id ?? "") : "");
            setMenu(null);
          }}
        />
      )}
      {organize && (
        <Dialog
          title={organize.action.replaceAll("_", " ")}
          onClose={() => setOrganize(null)}
        >
          {organize.action === "move" ? (
            <label>
              Folder
              <Choice
                label="Move to folder"
                value={folderName}
                onChange={setFolderName}
                options={[
                  { value: "", label: "Unfiled" },
                  ...library.folders.map((value) => ({ value, label: value })),
                ]}
              />
            </label>
          ) : organize.action === "remove_folder" ? (
            <p>Workflows stay available in Unfiled.</p>
          ) : (
            <label>
              Folder name
              <input
                value={folderName}
                onChange={(e) => setFolderName(e.target.value)}
              />
            </label>
          )}
          <div className="actions">
            <button onClick={() => setOrganize(null)}>Cancel</button>
            <button
              disabled={working}
              onClick={() =>
                void act(async () => {
                  setLibrary(
                    await api<Library>(
                      "organize",
                      {
                        action: organize.action,
                        old: organize.old,
                        name:
                          organize.action === "remove_folder"
                            ? organize.old
                            : folderName,
                        folder: folderName,
                      },
                      organize.id,
                    ),
                  );
                  setOrganize(null);
                  setFolder("*");
                })
              }
            >
              Save
            </button>
          </div>
        </Dialog>
      )}
      {history.length > 0 && (
        <details>
          <summary>Previous preview runs ({history.length})</summary>
          {history.slice(0, 30).map((run) => (
            <p key={run.run_id}>
              <a
                href={`/reports/${run.run_id}/report.html`}
                target="_blank"
                rel="noreferrer"
              >
                {run.name}
              </a>{" "}
              · {run.status} · <small>{run.run_id}</small>
            </p>
          ))}
        </details>
      )}
      <footer>
        Local execution · MIT licensed · Preview workflows and evidence use
        separate storage.
      </footer>
    </main>
  );
}
