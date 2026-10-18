"""Thin command-line adapter shared by installed wheel and source development."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from release_workbench import __version__
from release_workbench.application.runtime import Run
from release_workbench.application.starters import TEMPLATES, starter
from release_workbench.infrastructure.documents import (
    DocumentStore,
    compile_document,
    render_document,
)
from release_workbench.infrastructure.services import LocalServices

from .server import serve


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="workbench",
        description="Open your local automation dashboard, or create a project.",
        epilog="Start here: workbench | workbench serve | workbench run | workbench create. "
        "Terminal execution: workbench run --non-interactive.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", title="commands")
    for name in ("serve", "run", "create", "init", "validate", "report"):
        sub = commands.add_parser(
            name,
            help={
                "serve": "Open the browser dashboard (default)",
                "run": "Open the dashboard; use --non-interactive for terminal execution",
                "create": "Create a blank project here and open its dashboard",
                "init": "Advanced: create a starter YAML without serving",
                "validate": "Advanced: check YAML readiness",
                "report": "Advanced: locate a saved report",
            }[name],
        )
        sub.add_argument("--config", type=Path, default=Path("workflow-workbench.yaml"))
        sub.add_argument("--storage", type=Path, default=Path.home() / ".workbench-preview-v3")
        if name in ("init", "create"):
            sub.add_argument("--name")
        if name == "init":
            sub.add_argument("--template", choices=list(TEMPLATES))
        if name == "run":
            sub.add_argument("--non-interactive", action="store_true")
            sub.add_argument("--input", action="append", default=[])
            sub.add_argument("--resume")
            sub.add_argument("--retry-interrupted", action="store_true")
        if name in ("serve", "run", "create"):
            if name != "create":
                sub.add_argument("--project", type=Path, default=Path.cwd())
            sub.add_argument("--port", type=int, default=3104)
            sub.add_argument("--no-open", action="store_true")
        if name == "report":
            sub.add_argument("--run", required=True)
    arguments = sys.argv[1:]
    if (
        not arguments
        or arguments[0].startswith("--")
        and arguments[0] not in ("--help", "--version")
    ):
        arguments = ["serve", *arguments]
    args = parser.parse_args(arguments)
    try:
        if args.command == "create":
            from release_workbench.infrastructure.projects import create_project

            name = args.name or input("Project name [My workflow]: ").strip() or "My workflow"
            filename = args.config
            if filename == Path("workflow-workbench.yaml") and not args.name:
                filename = Path(
                    input("YAML filename [workflow-workbench.yaml]: ").strip() or str(filename)
                )
            entry = create_project(Path.cwd(), filename, name, args.storage)
            print(f"Created {Path.cwd() / filename}. No workflow commands have been started.")
            serve(Path.cwd(), args.storage, args.port, not args.no_open, entry["id"])
        elif args.command == "init":
            name = args.name or input("Workflow name: ").strip() or "My workflow"
            template = (
                args.template
                or input("Template (" + ", ".join(TEMPLATES) + ") [blank]: ").strip()
                or "blank"
            )
            value = starter(name, template)
            compile_document(value)
            with args.config.open("x", encoding="utf-8") as stream:
                stream.write(render_document(value))
            print(f"Created {args.config}. Open the browser to connect and configure cards.")
        elif args.command == "serve" or args.command == "run" and not args.non_interactive:
            serve(args.project, args.storage, args.port, not args.no_open)
        elif args.command == "report":
            file = (args.storage / "runs" / args.run / "report.html").resolve()
            if not file.is_relative_to((args.storage / "runs").resolve()) or not file.is_file():
                raise ValueError("Report does not exist inside Workbench storage.")
            print(file)
        else:
            workflow = compile_document(DocumentStore(args.config).read()["workflow"])
            if args.command == "validate":
                print("Valid schema v3 workflow: " + workflow.name)
            else:
                inputs = {}
                for argument in args.input:
                    key, separator, value = argument.partition("=")
                    if not separator:
                        raise ValueError("Inputs use NAME=JSON_OR_TEXT.")
                    try:
                        inputs[key] = json.loads(value)
                    except ValueError:
                        inputs[key] = value
                run = Run(
                    workflow,
                    args.config.resolve().parent,
                    args.storage / "runs",
                    LocalServices(),
                    inputs,
                    interactive=False,
                    resume=args.resume,
                    retry=args.retry_interrupted,
                    stack=(args.config.resolve(),),
                )
                try:
                    code = asyncio.run(run.execute())
                except KeyboardInterrupt:
                    run.stop()
                    code = 130
                print("Status: " + run.evidence.state["status"])
                print("Report: " + str(run.evidence.directory / "report.html"))
                if run.evidence.state.get("error"):
                    print(run.evidence.state["error"], file=sys.stderr)
                raise SystemExit(code)
    except (ValueError, OSError, KeyError, EOFError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
