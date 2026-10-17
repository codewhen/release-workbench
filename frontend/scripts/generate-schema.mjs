import { compile } from "json-schema-to-typescript";
import { readFile, writeFile, mkdir } from "node:fs/promises";
const schema = JSON.parse(
  await readFile(
    new URL("../../src/release_workbench/schema.json", import.meta.url),
    "utf8",
  ),
);
schema.title = "WorkflowDocument";
await mkdir(new URL("../src/shared/", import.meta.url), { recursive: true });
await writeFile(
  new URL("../src/shared/workflow.generated.ts", import.meta.url),
  await compile(schema, "WorkflowDocument", {
    bannerComment:
      "/* Generated from the public v3 JSON Schema. Do not edit by hand. */",
    additionalProperties: false,
  }),
);
