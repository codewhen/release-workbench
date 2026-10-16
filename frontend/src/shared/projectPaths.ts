/** Compare native project paths without assuming the host uses POSIX separators. */
function normalized(path: string): string {
  const windows = /^[a-z]:[\\/]/i.test(path) || path.startsWith("\\\\");
  return (windows ? path.replaceAll("\\", "/").toLowerCase() : path).replace(
    /\/+$/,
    "",
  );
}
export function belongsToProject(file: string, project: string): boolean {
  return normalized(file).startsWith(normalized(project) + "/");
}
