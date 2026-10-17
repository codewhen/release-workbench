# Glossary

| Word | Meaning |
|---|---|
| Approval | A manual evidence step returning Void |
| Binding | A constant/reference/wire supplying a field or named input |
| Boolean | Genuine true/false data, distinct from text and failure |
| Branch | An explicit If path or Parallel owned region |
| Card | A configured operation or control-flow element |
| Condition function | A function declared to return Boolean |
| Coordinator | Shared operation budget/resources used by a run and its children |
| Draft | Unsaved browser changes or a submitted recovery copy |
| Entry | A card's incoming execution port |
| Evidence | Logs, events, attempts, values and reports saved for a run |
| Execution connection | Round-port wire that starts subsequent work |
| Exclusive | Operation waits for other work and prevents new scheduling while active |
| Finish | Main workflow's successful completion marker |
| Function | Reusable graph with declared inputs and return type |
| Global | Declared typed state shared within a run, reset for a fresh run |
| Graph | Cards and their execution/value connections |
| Join | Paired card exposing named typed Parallel branch outputs |
| Layout area | Visual organization that does not change execution scope |
| Library | Registered local project paths/workflow entries and organization folders |
| Named input | Argument bound to an operation/function input name |
| Null | An intentional JSON null payload |
| Owner | Explicit structural card/region controlling a branch or loop-body card |
| Port | A labeled execution or typed-value connection point |
| Project | Directory containing workflow YAML and its resources |
| Resource lock | Name used to serialize operations that share a device/tool |
| Resume | Reuse matching successful evidence without blindly repeating side effects |
| Retry | Repeat an eligible failed operation under an explicit policy |
| Return | Function/owned-region completion marker |
| Run | One execution with its own globals, attempts and saved evidence |
| Scope | Where inputs, intermediate results and loop/error context are available |
| Source fingerprint | Identity used to decide whether saved evidence matches current work |
| Starter | A separate example workflow to learn/copy from |
| Value connection | Square-port wire supplying data; never starts execution |
| Void | Successful completion with no payload, distinct from null |
| Workspace | Directory context for a workflow; selected by `workspace` relative to each YAML directory; defaults to `.` |

See [connections and values](values.md) and [completion markers](tutorials/completion.md) for worked explanations rather than just definitions.
