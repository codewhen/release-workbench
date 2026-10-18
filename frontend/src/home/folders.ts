export const parentFolder = (path: string) =>
  path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
export const folderName = (path: string) =>
  path.split("/").at(-1) || "My workspace";
export const withinFolder = (path: string, parent: string) =>
  path === parent || path.startsWith(parent + "/");
export function folderAncestors(path: string) {
  return path
    .split("/")
    .map((_, index, pieces) => pieces.slice(0, index + 1).join("/"));
}
