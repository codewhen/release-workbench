import { useSyncExternalStore } from "react";

export interface WorkbenchRoute {
  workflow: string | null;
  folder: string;
  project: string;
  query: string;
  view?: "run" | "edit";
  graph?: string;
  display?: "canvas" | "list" | "yaml";
  card?: string;
  panel?: "settings";
  run?: string;
}
const keys: Record<keyof WorkbenchRoute, string> = {
  workflow: "workflow",
  folder: "folder",
  project: "project",
  query: "q",
  view: "view",
  graph: "graph",
  display: "display",
  card: "card",
  panel: "panel",
  run: "run",
};
const decodePart = (part: string) => {
  try {
    return decodeURIComponent(part);
  } catch {
    return part;
  }
};
export function readRoute(href: string): WorkbenchRoute {
  const url = new URL(href, "http://localhost");
  const params = url.searchParams;
  const view = params.get("view"),
    display = params.get("display");
  const route: WorkbenchRoute = {
    workflow: params.get("workflow") || null,
    run: params.get("run") || undefined,
    folder: params.get("folder") || "",
    project: params.get("project") || "*",
    query: params.get("q") || "",
    view: view === "run" || view === "edit" ? view : undefined,
    graph: params.get("graph") || undefined,
    display:
      display === "canvas" || display === "list" || display === "yaml"
        ? display
        : undefined,
    card: params.get("card") || undefined,
    panel: params.get("panel") === "settings" ? "settings" : undefined,
  };
  const parts = url.pathname.split("/").filter(Boolean).map(decodePart);
  if (parts[0] === "workspace") {
    route.workflow = null;
    route.folder = "";
  } else if (parts[0] === "folders") {
    route.workflow = null;
    route.folder = parts.slice(1).join("/");
  } else if (parts[0] === "workflows") {
    route.workflow = parts[1] || null;
    if (!route.workflow) route.folder = "*";
    else {
      let at = 2;
      if (parts[at] === "run" || parts[at] === "edit")
        route.view = parts[at++] as "run" | "edit";
      if (["canvas", "list", "yaml"].includes(parts[at]))
        route.display = parts[at++] as "canvas" | "list" | "yaml";
      if (parts[at] === "functions") {
        route.graph = parts[at + 1];
        at += 2;
      }
      if (parts[at] === "cards") {
        route.card = parts[at + 1];
        at += 2;
      }
      if (parts[at] === "settings") route.panel = "settings";
    }
  }
  return route;
}
export function routeHref(
  href: string,
  patch: Partial<WorkbenchRoute>,
): string {
  const url = new URL(href, "http://localhost");
  const previous = readRoute(href);
  const route = { ...previous, ...patch };
  if (patch.workflow !== undefined && patch.workflow !== previous.workflow)
    route.run = patch.run;
  for (const name of Object.values(keys)) url.searchParams.delete(name);
  if (route.project && route.project !== "*")
    url.searchParams.set("project", route.project);
  if (route.query) url.searchParams.set("q", route.query);
  if (route.workflow) {
    url.pathname = "/workflows/" + encodeURIComponent(route.workflow);
    if (route.view || route.display)
      url.pathname += "/" + (route.view ?? "run");
    if (route.display) url.pathname += "/" + route.display;
    if (route.graph)
      url.pathname += "/functions/" + encodeURIComponent(route.graph);
    if (route.card) url.pathname += "/cards/" + encodeURIComponent(route.card);
    if (route.panel) url.pathname += "/settings";
    if (route.run) url.searchParams.set("run", route.run);
    // Preserve the Home return location without mixing it into the workflow path.
    if (route.folder) url.searchParams.set("folder", route.folder);
  } else if (route.folder === "*") url.pathname = "/workflows";
  else if (route.folder)
    url.pathname =
      "/folders/" + route.folder.split("/").map(encodeURIComponent).join("/");
  else url.pathname = "/workspace";
  return url.pathname + url.search + url.hash;
}

type Blocker = (next: WorkbenchRoute, proceed: () => void) => boolean;
let blocker: Blocker | null = null;
let initialized = false,
  href = "",
  index = 0,
  reverting = false,
  allowedPop = false,
  bypass = false;
const listeners = new Set<() => void>();
const publish = () => {
  href = location.href;
  for (const listener of listeners) listener();
};
function initialize() {
  if (initialized) return;
  initialized = true;
  index = Number(history.state?.workbenchIndex ?? 0);
  history.replaceState(
    { ...history.state, workbenchIndex: index },
    "",
    routeHref(location.href, {}),
  );
  href = location.href;
  addEventListener("popstate", () => {
    if (reverting) {
      reverting = false;
      return;
    }
    const targetHref = location.href;
    const targetIndex = Number(history.state?.workbenchIndex ?? index);
    const proceed = () => {
      if (targetIndex === index) commit(targetHref, false);
      else {
        allowedPop = true;
        history.go(targetIndex - index);
      }
    };
    if (!allowedPop && blocker && !blocker(readRoute(targetHref), proceed)) {
      if (targetIndex === index)
        history.replaceState(
          { ...history.state, workbenchIndex: index },
          "",
          href,
        );
      else {
        reverting = true;
        history.go(index - targetIndex);
      }
      return;
    }
    allowedPop = false;
    index = targetIndex;
    history.replaceState(
      { ...history.state, workbenchIndex: index },
      "",
      routeHref(location.href, {}),
    );
    publish();
  });
}
function commit(next: string, replace: boolean) {
  if (
    next === location.href ||
    new URL(next, location.href).href === location.href
  )
    return;
  if (!replace) index += 1;
  history[replace ? "replaceState" : "pushState"](
    { ...history.state, workbenchIndex: index },
    "",
    next,
  );
  publish();
}
export function navigate(patch: Partial<WorkbenchRoute>, replace = false) {
  initialize();
  const next = routeHref(location.href, patch);
  const proceed = () => commit(next, replace);
  if (!bypass && blocker && !blocker(readRoute(next), proceed)) return;
  proceed();
}
export function allowNavigation(action: () => void) {
  bypass = true;
  try {
    action();
  } finally {
    bypass = false;
  }
}
export function blockNavigation(next: Blocker) {
  blocker = next;
  return () => {
    if (blocker === next) blocker = null;
  };
}
export function useLocation() {
  initialize();
  const current = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    () => href,
  );
  return readRoute(current);
}
