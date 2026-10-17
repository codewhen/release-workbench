import {
  Folder,
  FolderPlus,
  GitBranch,
  ChevronRight,
  Files,
} from "lucide-react";
import type { Library } from "../shared/types";
import type { MenuState } from "../editor/ContextMenu";
import { Choice } from "../components/Choice";
import { belongsToProject } from "../shared/projectPaths";
import {
  folderAncestors,
  folderName,
  parentFolder,
  withinFolder,
} from "./folders";

interface Props {
  library: Library;
  folder: string;
  project: string;
  query: string;
  onFolder: (folder: string) => void;
  onProject: (project: string) => void;
  onQuery: (query: string) => void;
  onOpen: (id: string) => void;
  onNewFolder: (parent: string) => void;
  onCreate: () => void;
  onRefresh: () => void;
  onRemoveProject: () => void;
  onMenu: (menu: MenuState) => void;
}
export function LibraryBrowser(props: Props) {
  const { library, folder, project, query } = props;
  const search = query.trim().toLowerCase();
  const missingFolder =
    library.projects.length > 0 &&
    folder !== "*" &&
    folder !== "" &&
    !library.folders.includes(folder);
  const entries = library.entries.filter(
    (entry) =>
      (project === "*" || belongsToProject(entry.path, project)) &&
      (search
        ? folder === "*" || folder === "" || withinFolder(entry.folder, folder)
        : folder === "*" || entry.folder === folder) &&
      (entry.name + " " + entry.path).toLowerCase().includes(search),
  );
  const folders = library.folders.filter((path) =>
    search
      ? (folder === "*" || folder === "" || withinFolder(path, folder)) &&
        path.toLowerCase().includes(search)
      : parentFolder(path) === (folder === "*" ? "" : folder),
  );
  const menu = (
    event: React.MouseEvent | React.KeyboardEvent,
    kind: "card" | "area",
    id: string,
  ) => {
    event.preventDefault();
    const box = event.currentTarget.getBoundingClientRect();
    props.onMenu({
      kind,
      id,
      x: "clientX" in event ? event.clientX : box.left + 20,
      y: "clientY" in event ? event.clientY : box.top + 20,
    });
  };
  const keyboardMenu = (
    event: React.KeyboardEvent,
    kind: "card" | "area",
    id: string,
  ) => {
    if ((event.shiftKey && event.key === "F10") || event.key === "ContextMenu")
      menu(event, kind, id);
  };
  const openFolder = (path: string) => {
    props.onFolder(path);
    props.onQuery("");
  };
  return (
    <div className="library-layout">
      <nav aria-label="Workflow folders" className="library-sidebar">
        <h3>Library</h3>
        <button onClick={() => props.onNewFolder(folder === "*" ? "" : folder)}>
          <FolderPlus size={17} />
          New folder
        </button>
        <button
          className="folder-button"
          aria-pressed={folder === ""}
          onClick={() => openFolder("")}
        >
          <Folder size={16} />
          My workspace
        </button>
        <button
          className="folder-button"
          aria-pressed={folder === "*"}
          onClick={() => openFolder("*")}
        >
          <Files size={16} />
          All workflows
        </button>
        {library.folders
          .filter((path) => !parentFolder(path))
          .map((path) => (
            <button
              key={path}
              className="folder-button"
              aria-pressed={withinFolder(folder, path)}
              onClick={() => openFolder(path)}
              onContextMenu={(event) => menu(event, "area", path)}
              onKeyDown={(event) => keyboardMenu(event, "area", path)}
            >
              <Folder size={16} />
              <span>{folderName(path)}</span>
            </button>
          ))}
      </nav>
      <section className="library-content" aria-label="Workflow library">
        <div className="library-filter">
          <label>
            Find a workflow
            <input
              type="search"
              value={query}
              onChange={(event) => props.onQuery(event.target.value)}
            />
          </label>
          <label>
            Project
            <Choice
              label="Project"
              value={project}
              onChange={props.onProject}
              options={[
                { value: "*", label: "All projects" },
                ...library.projects.map((value) => ({ value, label: value })),
              ]}
            />
          </label>
          {project !== "*" && (
            <button onClick={props.onRemoveProject}>
              Remove project from Home
            </button>
          )}
          <button onClick={props.onRefresh}>Refresh</button>
        </div>
        <nav className="library-breadcrumbs" aria-label="Folder breadcrumbs">
          <button
            onClick={() => openFolder("")}
            aria-current={folder === "" ? "page" : undefined}
          >
            My workspace
          </button>
          {folder === "*" ? (
            <>
              <ChevronRight size={15} />
              <span aria-current="page">All workflows</span>
            </>
          ) : (
            folderAncestors(folder)
              .filter(Boolean)
              .map((path) => (
                <span className="breadcrumb-part" key={path}>
                  <ChevronRight size={15} />
                  <button
                    aria-current={path === folder ? "page" : undefined}
                    onClick={() => openFolder(path)}
                  >
                    {folderName(path)}
                  </button>
                </span>
              ))
          )}
        </nav>
        {folders.length > 0 && (
          <section aria-label="Folders" className="library-group">
            <h3>Folders</h3>
            <div className="folder-grid">
              {folders
                .sort((a, b) => a.localeCompare(b))
                .map((path) => (
                  <button
                    key={path}
                    className="folder-tile"
                    onClick={() => openFolder(path)}
                    onContextMenu={(event) => menu(event, "area", path)}
                    onKeyDown={(event) => keyboardMenu(event, "area", path)}
                    aria-label={"Open folder “" + folderName(path) + "”"}
                  >
                    <Folder size={25} />
                    <span>
                      <strong>{search ? path : folderName(path)}</strong>
                      <small>
                        {
                          library.folders.filter(
                            (child) => parentFolder(child) === path,
                          ).length
                        }{" "}
                        folders ·{" "}
                        {
                          library.entries.filter(
                            (entry) => entry.folder === path,
                          ).length
                        }{" "}
                        workflows
                      </small>
                    </span>
                  </button>
                ))}
            </div>
          </section>
        )}
        {entries.length > 0 && (
          <section aria-label="Workflows" className="library-group">
            <h3>{search ? "Matching workflows" : "Workflows"}</h3>
            <div className="workflow-grid">
              {entries.map((entry) => (
                <article
                  className="workflow-row workflow-tile"
                  key={entry.id}
                  tabIndex={0}
                  onContextMenu={(event) => menu(event, "card", entry.id)}
                  onKeyDown={(event) => keyboardMenu(event, "card", entry.id)}
                  onDoubleClick={() =>
                    entry.supported && props.onOpen(entry.id)
                  }
                >
                  <div className="workflow-tile-heading">
                    <GitBranch size={22} />
                    <h3>{entry.name}</h3>
                  </div>
                  <p className="path" title={entry.path}>
                    {entry.path}
                  </p>
                  <small className={entry.error ? "error" : "muted"}>
                    {entry.error ?? (entry.folder || "My workspace")}
                  </small>
                  <div className="actions">
                    <button
                      disabled={!entry.supported}
                      onClick={() => props.onOpen(entry.id)}
                    >
                      Open workflow
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
        {!entries.length && !folders.length && (
          <div className="empty">
            <Folder size={28} />
            <h3>
              {missingFolder
                ? "Folder not found"
                : search
                  ? "No matching items"
                  : "This folder is empty"}
            </h3>
            <p>
              {missingFolder
                ? "This folder may have been renamed or removed. Open My workspace to continue."
                : search
                  ? "Try another name or clear the search."
                  : "Add a subfolder or create a workflow to get started."}
            </p>
            {missingFolder ? (
              <button onClick={() => openFolder("")}>Go to My workspace</button>
            ) : (
              !search && (
                <button onClick={props.onCreate}>Create a workflow</button>
              )
            )}
          </div>
        )}
      </section>
    </div>
  );
}
