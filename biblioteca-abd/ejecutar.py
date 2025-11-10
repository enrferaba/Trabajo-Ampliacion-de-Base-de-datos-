"""Convenience script to bootstrap the Biblioteca ABD stack."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run common docker compose workflows for the Biblioteca ABD project",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="up",
        choices={"up", "down", "logs", "restart"},
        help="Docker compose action to execute (default: up).",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Rebuild images before starting containers when using the 'up' action.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip image rebuild when using the 'up' action (overrides --build).",
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Run services in the background when using the 'up' action.",
    )
    parser.add_argument(
        "--services",
        nargs="*",
        default=(),
        help="Optional list of services to scope the action to.",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Stream logs when using the 'logs' action.",
    )
    return parser.parse_args()


def run_compose(args: argparse.Namespace) -> int:
    project_root = Path(__file__).resolve().parent
    compose_file = project_root / "compose.yml"
    if not compose_file.exists():
        raise SystemExit("compose.yml not found. Run this script from the repository root.")

    base_cmd = ["docker", "compose", "-f", str(compose_file)]

    if args.build and args.no_build:
        raise SystemExit("Cannot use --build and --no-build together.")

    if args.action == "up":
        cmd = base_cmd + ["up"]
        should_build = args.build or not args.no_build
        if should_build:
            cmd.append("--build")
        if args.detach:
            cmd.append("-d")
        cmd.extend(args.services)
    elif args.action == "down":
        cmd = base_cmd + ["down"]
        cmd.extend(args.services)
    elif args.action == "logs":
        cmd = base_cmd + ["logs"]
        if args.follow:
            cmd.append("-f")
        cmd.extend(args.services)
    else:  # restart
        cmd = base_cmd + ["restart"]
        cmd.extend(args.services)

    try:
        print("Ejecutando:", " ".join(cmd))
        completed = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    if args.action == "up" and args.detach and not args.services:
        logs_cmd = base_cmd + ["logs", "-f"]
        print("Servicios levantados en segundo plano. Mostrando logs (Ctrl+C para salir)...")
        try:
            subprocess.run(logs_cmd, check=False)
        except KeyboardInterrupt:
            print("\nInterrupción solicitada por el usuario, los servicios siguen en ejecución.")
    return completed.returncode


def main() -> int:
    args = parse_args()
    return run_compose(args)


if __name__ == "__main__":
    sys.exit(main())
