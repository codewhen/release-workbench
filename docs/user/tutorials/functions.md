# Build and use functions

A function is a reusable flowchart with declared inputs and return type. It is useful for a repeated operation, an isolated data transformation or a condition used by If, While and Poll.

## Create Compose greeting

1. Open **Edit → Workflow settings → Create function**, or use **Create function** beside a card's function selector.
2. In the **Create a function** dialog enter its name and choose **Return type** `string`, then create it. Condition-card creation preselects Boolean.
3. In its dedicated graph, leave cards unselected (click empty canvas) to show **Function flowchart → Function inputs** in the left panel. Enter `name`, choose **Add input**, select type string and enable **Required without default**. It starts with Start and Return, not Finish.
4. Add Python between them, choose Return type string, and enter `return "Hello " + inputs["name"]`.
5. On Python add Named input `name` with source **Input · name**. Declaring the function argument alone does not populate every card's inputs dictionary.
6. On Return select Python as Result source. Connect Start → Python → Return and validate.
7. Use **Back to caller** to return to main.

![A dedicated function flowchart with its completion marker](../../assets/screenshots/function-view.png)

## Call the function

Add **Call function**, choose Compose greeting, and pass a constant `Reader` under Named inputs name. Connect it into main's sequence. Select Call function as Finish's result. Run the [complete example](../../examples/call.yaml): the result is `Hello Reader`.

Function inputs can have defaults and descriptions. Missing defaults make them required. Callers must supply compatible values. Each invocation gets independent inputs and intermediate results, so reusing a function does not leak the previous call's card results. Declared run globals are shared; use that deliberately and consider parallel conflicts.

## Boolean condition functions

If, While and Poll select a function declared Boolean and invoke it themselves; an extra Call function card is unnecessary just to use their condition.

For a variable check: declare count, then inside the condition wire Start → Variable Get count → Calculate less_than 3 → Return. Select Get count as Calculate's First value and Calculate as Return's result. For a manual decision, put Manual decision in that function and return its Boolean answer. For readiness, use Check path.

## Limits and ownership

Recursion is unsupported, including indirect recursion. A function cannot Break/Continue a loop owned by its caller. Put repetition in main-canvas loop wiring or inside the function's own legal loop. Returned data must be JSON-compatible and match the function declaration.

To run another project's complete workflow, use [External workspace](../cards/workspace.md): it starts its own globals and uses its own YAML directory. Functions instead remain within the same run/workspace and share run globals.
