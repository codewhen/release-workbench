import { describe, expect, it } from "vitest";
import { readRoute, routeHref } from "./location";

describe("readable Workbench paths", () => {
  it("retains invocation context within an editor and clears it when leaving", () => {
    const url = "/workflows/child/run?run=invocation-one";
    expect(readRoute(url).run).toBe("invocation-one");
    expect(routeHref(url, { card: "probe" })).toBe(
      "/workflows/child/run/cards/probe?run=invocation-one",
    );
    expect(routeHref(url, { workflow: "other" })).not.toContain("run=");
    expect(routeHref(url, { workflow: null })).toBe("/workspace");
  });
  it("canonicalizes the workspace, collection and legacy links", () => {
    expect(routeHref("/", {})).toBe("/workspace");
    expect(routeHref("/?folder=*", {})).toBe("/workflows");
    expect(routeHref("/?workflow=example&view=edit&display=list", {})).toBe(
      "/workflows/example/edit/list",
    );
    expect(readRoute("/workspace")).toMatchObject({
      folder: "",
      project: "*",
      workflow: null,
    });
    expect(readRoute("/workflows")).toMatchObject({
      folder: "*",
      workflow: null,
    });
  });
  it("round-trips nested Unicode folder paths and query filters", () => {
    const url = routeHref("/workspace", {
      folder: "Automation/Phone & tablet",
      query: "é check",
      project: "/example/workspace",
    });
    expect(url).toMatch(/^\/folders\/Automation\/Phone%20%26%20tablet\?/);
    expect(readRoute(url)).toMatchObject({
      folder: "Automation/Phone & tablet",
      query: "é check",
      project: "/example/workspace",
    });
  });
  it("puts editor pages, functions, selections and settings in the path", () => {
    const url = routeHref("/workflows/example", {
      view: "edit",
      graph: "is-ready",
      display: "list",
      card: "result",
      panel: "settings",
    });
    expect(url).toBe(
      "/workflows/example/edit/list/functions/is-ready/cards/result/settings",
    );
    expect(readRoute(url)).toMatchObject({
      workflow: "example",
      view: "edit",
      graph: "is-ready",
      display: "list",
      card: "result",
      panel: "settings",
    });
  });
  it("retains the folder return context only while inspecting a workflow", () => {
    const editor = routeHref("/folders/Automation/Checks", {
      workflow: "example",
    });
    expect(editor).toBe("/workflows/example?folder=Automation%2FChecks");
    expect(routeHref(editor, { workflow: null })).toBe(
      "/folders/Automation/Checks",
    );
  });
  it("omits defaults and safely ignores malformed optional editor fields", () => {
    expect(
      routeHref("/?folder=Tests&project=project&view=edit", {
        folder: "",
        project: "*",
        view: undefined,
      }),
    ).toBe("/workspace");
    expect(
      readRoute("/?view=unknown&display=unknown&panel=unknown"),
    ).toMatchObject({ view: undefined, display: undefined, panel: undefined });
    expect(() => readRoute("/folders/%not-encoded")).not.toThrow();
  });
});
