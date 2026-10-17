import { describe, it, expect } from "vitest";
import { belongsToProject } from "./projectPaths";
describe("project directory filtering", () => {
  it("matches POSIX projects without matching adjacent directory names", () => {
    expect(belongsToProject("/work/app/flow.yaml", "/work/app")).toBe(true);
    expect(belongsToProject("/work/app-copy/flow.yaml", "/work/app")).toBe(
      false,
    );
  });
  it("handles Windows drive paths and case differences", () => {
    expect(belongsToProject("C:\\Work\\App\\flow.yaml", "c:\\work\\app")).toBe(
      true,
    );
    expect(belongsToProject("C:/Work/App/flow.yaml", "C:\\Work\\App\\")).toBe(
      true,
    );
    expect(belongsToProject("C:\\Work\\App2\\flow.yaml", "C:\\Work\\App")).toBe(
      false,
    );
  });
  it("handles UNC projects and drive roots", () => {
    expect(
      belongsToProject(
        "\\\\server\\share\\app\\flow.yaml",
        "\\\\server\\share\\app",
      ),
    ).toBe(true);
    expect(belongsToProject("D:\\flow.yaml", "D:\\")).toBe(true);
  });
});
