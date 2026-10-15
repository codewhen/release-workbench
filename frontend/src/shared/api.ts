const token =
  document.querySelector<HTMLMetaElement>('meta[name="workbench-token"]')
    ?.content ?? "";
export async function api<T>(
  route: string,
  body?: unknown,
  workflow?: string,
): Promise<T> {
  const response = await fetch(
    `/api/${route}${workflow ? "?workflow=" + encodeURIComponent(workflow) : ""}`,
    {
      method: body === undefined ? "GET" : "POST",
      headers:
        body === undefined
          ? {}
          : { "Content-Type": "application/json", "X-Workbench-Token": token },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
  );
  const value: unknown = await response.json();
  if (!response.ok)
    throw Error(
      typeof value === "object" && value !== null && "error" in value
        ? String(value.error)
        : "Request failed.",
    );
  return value as T;
}
