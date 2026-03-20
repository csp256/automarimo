from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

APP_NAME = "automarimo"
DEFAULT_CONFIG = {
    "editor_command": None,
    "marimo_args": [
        "run",
        "--with",
        "marimo",
        "marimo",
        "edit",
        "--sandbox",
        "--watch"
    ],
    "auto_install_uv": True,
    "uv_install_dir": ".\\vendor\\uv",
    "debug": False
}


@dataclass(frozen=False)
class Config:
    editor_command: list[str] | None
    marimo_args: list[str]
    auto_install_uv: bool
    uv_install_dir: Path
    debug: bool


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
LOG_PATH = SCRIPT_DIR / "automarimo.log"


class AutomarimoError(Exception):
    pass


class EditorNotFoundError(AutomarimoError):
    pass


class UvInstallError(AutomarimoError):
    pass


class UserFacingError(AutomarimoError):
    pass



def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)



def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")



def write_config_dict(raw: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")



def load_config_dict() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        write_config_dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UserFacingError(f"Invalid JSON in config file: {CONFIG_PATH}\n{exc}") from exc

    if not isinstance(raw, dict):
        raise UserFacingError(f"Config file must contain a JSON object: {CONFIG_PATH}")

    merged = dict(DEFAULT_CONFIG)
    merged.update(raw)
    return merged



def load_config() -> Config:
    raw = load_config_dict()

    editor_command = raw.get("editor_command", DEFAULT_CONFIG["editor_command"])
    marimo_args = raw.get("marimo_args", DEFAULT_CONFIG["marimo_args"])
    auto_install_uv = raw.get("auto_install_uv", DEFAULT_CONFIG["auto_install_uv"])
    uv_install_dir_raw = raw.get("uv_install_dir", DEFAULT_CONFIG["uv_install_dir"])
    debug = raw.get("debug", DEFAULT_CONFIG["debug"])

    if editor_command is not None:
        if not isinstance(editor_command, list) or not all(isinstance(x, str) for x in editor_command) or not editor_command:
            raise UserFacingError("config.json: editor_command must be null or a non-empty list of strings")
    if not isinstance(marimo_args, list) or not all(isinstance(x, str) for x in marimo_args) or not marimo_args:
        raise UserFacingError("config.json: marimo_args must be a non-empty list of strings")
    if not isinstance(auto_install_uv, bool):
        raise UserFacingError("config.json: auto_install_uv must be true or false")
    if not isinstance(uv_install_dir_raw, str) or not uv_install_dir_raw:
        raise UserFacingError("config.json: uv_install_dir must be a non-empty string")
    if not isinstance(debug, bool):
        raise UserFacingError("config.json: debug must be true or false")

    uv_install_dir = expand_local_path(uv_install_dir_raw)
    return Config(
        editor_command=editor_command,
        marimo_args=marimo_args,
        auto_install_uv=auto_install_uv,
        uv_install_dir=uv_install_dir,
        debug=debug,
    )



def save_editor_command(cfg: Config, editor_command: list[str]) -> None:
    raw = load_config_dict()
    raw["editor_command"] = editor_command
    write_config_dict(raw)
    cfg.editor_command = editor_command
    log(f"Saved editor_command: {editor_command!r}")



def expand_local_path(value: str) -> Path:
    p = Path(value)
    if not p.is_absolute():
        p = SCRIPT_DIR / p
    return p.resolve()


def converted_marimo_path_for_ipynb(path: Path) -> Path:
    stem = path.with_suffix("").name
    return path.with_name(f"{stem}_marimo.py")


def maybe_debug(cfg: Config, message: str) -> None:
    log(message)
    if cfg.debug:
        print(message)



def print_usage() -> None:
    print(
        f"Usage: {Path(sys.argv[0]).name} [--dry-run] [--debug] FILE.py|FILE.ipynb\n"
        f"       {Path(sys.argv[0]).name} --print-config-path\n"
        f"       {Path(sys.argv[0]).name} --print-log-path\n"
    )



def parse_args(argv: list[str]) -> tuple[Path | None, bool, bool, bool, bool]:
    dry_run = False
    force_debug = False
    print_config_path = False
    print_log_path = False
    target: Path | None = None

    for arg in argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--debug":
            force_debug = True
        elif arg == "--print-config-path":
            print_config_path = True
        elif arg == "--print-log-path":
            print_log_path = True
        elif arg.startswith("-"):
            raise UserFacingError(f"Unknown option: {arg}")
        else:
            if target is not None:
                raise UserFacingError("Please provide exactly one target file")
            target = Path(arg)

    return target, dry_run, force_debug, print_config_path, print_log_path



def is_marimo_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name == "marimo" for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module == "marimo"
    return False



def assigned_marimo_app_names(tree: ast.AST) -> set[str]:
    app_names: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue

        fn = node.value.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "App" and isinstance(fn.value, ast.Name)):
            continue

        for target in node.targets:
            if isinstance(target, ast.Name):
                app_names.add(target.id)

    return app_names



def has_cell_decorator_or_setup_block(tree: ast.AST, app_names: set[str]) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if (
                    isinstance(target, ast.Attribute)
                    and target.attr == "cell"
                    and isinstance(target.value, ast.Name)
                    and target.value.id in app_names
                ):
                    return True
                
        if isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if (
                    isinstance(ctx, ast.Attribute)
                    and ctx.attr == "setup"
                    and isinstance(ctx.value, ast.Name)
                    and ctx.value.id in app_names
                ):
                    return True
    return False



def is_probably_marimo_notebook(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="utf-8", errors="replace")

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return False

    has_import = any(is_marimo_import(node) for node in tree.body)
    if not has_import:
        return False

    app_names = assigned_marimo_app_names(tree)
    if not app_names:
        return False

    return has_cell_decorator_or_setup_block(tree, app_names)



def command_looks_like_placeholder(cmd: list[str] | None) -> bool:
    if not cmd:
        return True
    return cmd == ["code", "--reuse-window"]



def normalize_editor_command(cmd: list[str]) -> list[str]:
    exe = cmd[0]
    resolved = shutil.which(exe)
    if resolved:
        return [resolved, *cmd[1:]]
    if Path(exe).exists():
        return [str(Path(exe).resolve()), *cmd[1:]]
    return cmd


def append_existing_editor_candidate(candidates: list[list[str]], exe: Path, extra: list[str] | None = None) -> None:
    if exe.exists():
        if extra is None:
            extra = []
        candidates.append([str(exe), *extra])


def windows_editor_candidates() -> list[list[str]]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("ProgramFiles", ""))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", ""))

    candidates: list[list[str]] = []
    common_exes = [
        local / "Programs" / "Microsoft VS Code" / "Code.exe",
        local / "Programs" / "Cursor" / "Cursor.exe",
        local / "Programs" / "VSCodium" / "VSCodium.exe",
        program_files / "Microsoft VS Code" / "Code.exe",
        program_files_x86 / "Microsoft VS Code" / "Code.exe",
        program_files / "Cursor" / "Cursor.exe",
        program_files_x86 / "Cursor" / "Cursor.exe",
        program_files / "VSCodium" / "VSCodium.exe",
        program_files_x86 / "VSCodium" / "VSCodium.exe",
    ]

    jetbrains_common_exes = [
        program_files / "JetBrains" / "PyCharm" / "bin" / "pycharm64.exe",
        program_files_x86 / "JetBrains" / "PyCharm" / "bin" / "pycharm64.exe",
        local / "Programs" / "JetBrains" / "PyCharm" / "bin" / "pycharm64.exe",
        program_files / "JetBrains" / "IntelliJ IDEA" / "bin" / "idea64.exe",
        program_files_x86 / "JetBrains" / "IntelliJ IDEA" / "bin" / "idea64.exe",
        local / "Programs" / "JetBrains" / "IntelliJ IDEA" / "bin" / "idea64.exe",
    ]

    for exe in common_exes:
        if exe.exists():
            extra = ["--reuse-window"] if exe.name.lower() in {"code.exe", "cursor.exe", "vscodium.exe"} else []
            candidates.append([str(exe), *extra])

    for exe in jetbrains_common_exes:
        append_existing_editor_candidate(candidates, exe)

    for root in (
        program_files / "JetBrains",
        program_files_x86 / "JetBrains",
        local / "Programs" / "JetBrains",
    ):
        if root.exists():
            for exe in sorted(root.glob("PyCharm*\\bin\\pycharm64.exe"), reverse=True):
                append_existing_editor_candidate(candidates, exe)
            for exe in sorted(root.glob("IntelliJ IDEA*\\bin\\idea64.exe"), reverse=True):
                append_existing_editor_candidate(candidates, exe)

    for name in ("code", "cursor", "codium", "pycharm64", "pycharm", "idea64", "idea"):
        resolved = shutil.which(name)
        if resolved:
            extra = ["--reuse-window"] if name in {"code", "cursor", "codium"} else []
            candidates.append([resolved, *extra])

    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(candidate)
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def prompt_for_editor_path_windows() -> list[str] | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askopenfilename(
        title="Choose your code editor executable",
        filetypes=[("Applications", "*.exe"), ("All files", "*.*")],
    )
    root.destroy()
    if not selected:
        return None

    exe_name = Path(selected).name.lower()
    extra = ["--reuse-window"] if exe_name in {"code.exe", "cursor.exe", "vscodium.exe"} else []
    return [selected, *extra]



def prompt_for_editor_windows(cfg: Config) -> list[str]:
    log("showing editor picker")
    candidates = windows_editor_candidates()

    print("\nautomarimo setup")
    print("=================")
    print("Choose the editor to use for normal Python files.\n")

    if candidates:
        print("Detected editors:")
        for idx, candidate in enumerate(candidates, start=1):
            print(f"  {idx}. {candidate[0]}")
        print()
    else:
        print("No common editors were detected automatically.\n")

    browse_index = len(candidates) + 1
    default_index = len(candidates) + 2
    print(f"  {browse_index}. Browse for an editor executable...")
    print(f"  {default_index}. Use the current Windows default app for normal .py files")
    print()

    while True:
        choice = input(f"Enter a number [1-{default_index}]: ").strip()
        try:
            selected = int(choice)
        except ValueError:
            print("Please enter a number.")
            continue

        if 1 <= selected <= len(candidates):
            command = normalize_editor_command(candidates[selected - 1])
            save_editor_command(cfg, command)
            return command

        if selected == browse_index:
            command = prompt_for_editor_path_windows()
            if command is None:
                print("No editor selected.")
                continue
            command = normalize_editor_command(command)
            save_editor_command(cfg, command)
            return command

        if selected == default_index:
            save_editor_command(cfg, ["__WINDOWS_DEFAULT__"])
            print("Saved: use Windows default app for ordinary Python files.")
            return ["__WINDOWS_DEFAULT__"]

        print("Selection out of range.")


def ensure_editor_command_windows(cfg: Config) -> list[str]:
    configured = cfg.editor_command

    if configured == ["__WINDOWS_DEFAULT__"]:
        return configured

    if configured and not command_looks_like_placeholder(configured):
        normalized = normalize_editor_command(configured)
        exe = normalized[0]
        if Path(exe).exists() or shutil.which(exe):
            if normalized != configured:
                save_editor_command(cfg, normalized)
            return normalized
        log(f"Configured editor not found: {configured!r}")
    
    chosen = normalize_editor_command(prompt_for_editor_windows(cfg))
    return chosen


def build_editor_command(path: Path, cfg: Config) -> list[str] | None:
    if os.name == "nt":
        base = ensure_editor_command_windows(cfg)
        if base == ["__WINDOWS_DEFAULT__"]:
            return None
        return [*base, str(path)]

    if cfg.editor_command:
        base = normalize_editor_command(cfg.editor_command)
        exe = base[0]
        if Path(exe).exists() or shutil.which(exe):
            return [*base, str(path)]

    raise EditorNotFoundError(
        "Could not find the configured editor executable. Update config.json."
    )



def launch_editor(path: Path, cfg: Config, cmd: list[str] | None) -> int:
    # cmd = build_editor_command(path, cfg)
    if cmd is None:
        return launch_with_windows_default(path, cfg)
    maybe_debug(cfg, f"Launching editor: {cmd!r}")
    subprocess.Popen(cmd)
    return 0



def launch_with_windows_default(path: Path, cfg: Config) -> int:
    maybe_debug(cfg, f"Falling back to Windows default opener for: {path}")
    os.startfile(str(path))
    return 0



def locate_uv_candidates(install_dir: Path) -> list[Path]:
    return [
        install_dir / "uv.exe",
        install_dir / "bin" / "uv.exe",
        install_dir / "uv",
        install_dir / "bin" / "uv",
    ]



def resolve_uv_executable(cfg: Config) -> str | None:
    for candidate in locate_uv_candidates(cfg.uv_install_dir):
        if candidate.exists():
            return str(candidate)

    resolved = shutil.which("uv")
    if resolved:
        return resolved

    return None



def install_uv_windows(install_dir: Path, debug: bool = False) -> None:
    install_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        "& { $env:UV_UNMANAGED_INSTALL='" + str(install_dir) + "'; $env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex }",
    ]

    log(f"Installing uv to {install_dir}")
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        raise UvInstallError(
            f"Failed to install uv into {install_dir}.\n"
            "Please check automarimo.log and confirm PowerShell is allowed to download and run the official uv installer."
        )

    if not any(candidate.exists() for candidate in locate_uv_candidates(install_dir)):
        raise UvInstallError(
            f"uv installer completed but no uv executable was found in {install_dir}."
        )



def ensure_uv(cfg: Config) -> str:
    uv_exe = resolve_uv_executable(cfg)
    if uv_exe:
        maybe_debug(cfg, f"Using uv executable: {uv_exe}")
        return uv_exe

    if not cfg.auto_install_uv:
        raise UvInstallError(
            "uv was not found and auto_install_uv is false. Install uv manually or enable auto_install_uv in config.json."
        )

    if os.name != "nt":
        raise UvInstallError(
            "uv was not found. This portable build only auto-installs uv on Windows at the moment."
        )

    install_uv_windows(cfg.uv_install_dir, debug=cfg.debug)
    uv_exe = resolve_uv_executable(cfg)
    if not uv_exe:
        raise UvInstallError("uv installation finished, but automarimo still could not find uv.")

    maybe_debug(cfg, f"Installed uv executable: {uv_exe}")
    return uv_exe



def build_marimo_command(path: Path, cfg: Config) -> list[str]:
    uv_exe = ensure_uv(cfg)
    return [uv_exe, *cfg.marimo_args, str(path)]


def build_marimo_convert_command(input_path: Path, output_path: Path, cfg: Config) -> list[str]:
    uv_exe = ensure_uv(cfg)
    return [
        uv_exe,
        "run",
        "--with",
        "marimo",
        "marimo",
        "convert",
        str(input_path),
        "-o",
        str(output_path),
    ]


def run_foreground(cmd: Sequence[str], *, banner: str | None = None) -> int:
    if banner:
        print(banner, flush=True)
    completed = subprocess.run(list(cmd))
    return completed.returncode



def marimo_banner(path: Path) -> str:
    return (
        "\n"
        "============================================================\n"
        " automarimo\n"
        "============================================================\n"
        f" Notebook: {path}\n"
        "\n"
        " This window is running the marimo backend.\n"
        " Leave this window open while the notebook is in use.\n"
        " Closing this window will stop the notebook.\n"
        "\n"
        " When finished:\n"
        "   1. Close the browser tab\n"
        "   2. Then close this window\n"
        "============================================================\n"
    )


def validate_ipynb_structure(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise UserFacingError(
            f"File is not valid JSON, so it is not a valid Jupyter notebook:\n  {path}\n\n{e}"
        ) from e

    if not isinstance(data, dict):
        raise UserFacingError(
            f"Jupyter notebook must be a JSON object at top level:\n  {path}"
        )

    if "cells" not in data:
        raise UserFacingError(
            f"File does not appear to be a valid Jupyter notebook because it has no top-level 'cells' field:\n  {path}"
        )

    if not isinstance(data["cells"], list):
        raise UserFacingError(
            f"Jupyter notebook has a top-level 'cells' field, but it is not a list:\n  {path}"
        )


def convert_ipynb_to_marimo(path: Path, cfg: Config) -> Path:
    """
    Convert a Jupyter notebook to a sibling marimo .py file and return that path.
    """
    if path.suffix.lower() != ".ipynb":
        return path

    output_path = converted_marimo_path_for_ipynb(path)
    cmd = build_marimo_convert_command(path, output_path, cfg)
    maybe_debug(cfg, f"Converting Jupyter notebook with command: {cmd!r}")

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    maybe_debug(cfg, f"convert return code: {completed.returncode}")
    if completed.stdout:
        maybe_debug(cfg, f"convert stdout:\n{completed.stdout}")
    if completed.stderr:
        maybe_debug(cfg, f"convert stderr:\n{completed.stderr}")

    if completed.returncode != 0:
        raise UserFacingError(
            "Failed to convert Jupyter notebook to marimo:\n"
            f"  input:  {path}\n"
            f"  output: {output_path}\n"
            f"\nstdout:\n{completed.stdout or '(none)'}\n"
            f"\nstderr:\n{completed.stderr or '(none)'}"
        )

    if not output_path.exists():
        raise UserFacingError(
            f"marimo conversion reported success, but the output file was not created:\n"
            f"  {output_path}"
        )

    maybe_debug(cfg, f"Converted Jupyter notebook to marimo: {output_path}")
    return output_path


def seed_empty_file_from_default_notebook(path: Path, cfg: Config) -> bool:
    """
    If path is an empty .py file, copy the contents of default_notebook.py into it.
    Returns True if the file was modified.
    """
    if path.suffix.lower() != ".py":
        return False

    try:
        if path.stat().st_size != 0:
            return False
    except FileNotFoundError:
        return False

    default_notebook = SCRIPT_DIR / "default_notebook.py"
    if not default_notebook.exists() or not default_notebook.is_file():
        raise UserFacingError(
            f"Opened an empty Python file, but the default notebook template was not found: {default_notebook}"
        )

    contents = default_notebook.read_text(encoding="utf-8")
    path.write_text(contents, encoding="utf-8")
    maybe_debug(cfg, f"Seeded empty Python file from default notebook: {path}")
    return True

def run_target(path: Path, cfg: Config, *, dry_run: bool = False) -> int:
    if not path.exists():
        raise UserFacingError(f"File does not exist: {path}")
    if not path.is_file():
        raise UserFacingError(f"Not a file: {path}")

    path = path.resolve()

    if path.suffix.lower() == ".ipynb":
        maybe_debug(cfg, f"Converting jupyter notebook: {path}")
        validate_ipynb_structure(path)
        path = convert_ipynb_to_marimo(path, cfg)
    
    seeded_from_template = seed_empty_file_from_default_notebook(path, cfg)
    is_marimo = is_probably_marimo_notebook(path)
    maybe_debug(cfg, f"Target: {path}")
    maybe_debug(cfg, f"Seeded from default notebook: {seeded_from_template}")
    maybe_debug(cfg, f"Detected marimo notebook: {is_marimo}")

    if is_marimo:
        cmd = build_marimo_command(path, cfg)
        maybe_debug(cfg, f"Marimo command: {cmd!r}")
        if dry_run:
            print(json.dumps(cmd))
            return 0
        rc = run_foreground(cmd, banner=marimo_banner(path))
        if rc != 0 and os.name == "nt":
            input("\nmarimo exited with an error. Press Enter to close this window...")
        return rc

    cmd = build_editor_command(path, cfg)
    maybe_debug(cfg, f"Editor command: {cmd!r}")
    if dry_run:
        print(json.dumps(cmd))
        return 0

    try:
        return launch_editor(path, cfg, cmd)
    except EditorNotFoundError:
        raise
    except FileNotFoundError as exc:
        log(f"Editor launch FileNotFoundError: {exc}")
        if os.name == "nt":
            return launch_with_windows_default(path, cfg)
        raise EditorNotFoundError(str(exc)) from exc



def main(argv: list[str]) -> int:
    try:
        log(f"PID={os.getpid()} argv={sys.argv!r}")
        target, dry_run, force_debug, print_config_path, print_log_path = parse_args(argv)
        if print_config_path:
            print(CONFIG_PATH)
            return 0
        if print_log_path:
            print(LOG_PATH)
            return 0
        if target is None:
            print_usage()
            return 2

        cfg = load_config()
        if force_debug:
            cfg = Config(
                editor_command=cfg.editor_command,
                marimo_args=cfg.marimo_args,
                auto_install_uv=cfg.auto_install_uv,
                uv_install_dir=cfg.uv_install_dir,
                debug=True,
            )
        return run_target(target, cfg, dry_run=dry_run)
    except UserFacingError as exc:
        log(f"ERROR: {exc}")
        eprint(f"Error: {exc}")
        return 1
    except KeyboardInterrupt:
        eprint("Interrupted.")
        return 130
    except Exception as exc:
        log(f"UNEXPECTED ERROR: {exc!r}")
        eprint(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
