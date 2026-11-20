"""Exercise the shared dev entry point without a shell or global tool changes."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from docintel.config import ROOT


@pytest.fixture
def dev():
    spec = importlib.util.spec_from_file_location("dev_launcher", ROOT / "scripts/dev.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "version,code",
    [
        ((3, 11, 7), "python_unsupported"),
        ((3, 13, 0), "python_unsupported"),
        ((3, 14, 5), "dependencies_missing"),
    ],
)
def test_doctor_without_venv_preflights_before_backend_import(
    dev, tmp_path, monkeypatch, version, code
):
    package = tmp_path / "backend/src/docintel"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    # Importing this under the simulated old interpreter must fail compilation.
    # Supported Python instead exercises the missing-dependency report.
    (package / "doctor.py").write_text(
        "invalid syntax PRIVATE_CANARY\n"
        if version < (3, 14)
        else "raise ImportError('PRIVATE_CANARY dependency')\n"
    )
    (tmp_path / ".env").write_text("PRIVATE_CANARY=preserve\n")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["dev.py", "doctor", "--json", "--runtime", "missing"])
    real_run = subprocess.run
    results = []

    def selected_interpreter(argv, **kwargs):
        assert argv[0] == sys.executable  # No backend venv in this checkout.
        assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
        assert kwargs["timeout"] == 30 and not kwargs.get("shell", False)
        # Execute the actual bootstrap, including compile/import and SystemExit,
        # with controlled version metadata; do not mock a successful report.
        argv[2] = "import sys\nsys.version_info = " + repr(version) + "\n" + argv[2]
        result = real_run(argv, **kwargs, capture_output=True, text=True)
        results.append(result)
        return result

    monkeypatch.setattr(dev.subprocess, "run", selected_interpreter)
    with pytest.raises(SystemExit) as exited:
        dev.main()
    assert exited.value.code == 1
    result = results[0]
    report = json.loads(result.stdout)
    assert report["report_version"] == 1 and report["status"] == "action_required"
    assert report["checks"][0]["code"] == code and report["checks"][0]["action"]
    assert not result.stderr and "PRIVATE_CANARY" not in result.stdout
    assert str(tmp_path) not in result.stdout
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("task", ["setup", "frontend", "frontend-check", "e2e", "check"])
def test_windows_npm_entry_points_resolve_launcher(dev, tmp_path, monkeypatch, task):
    launcher = str(tmp_path / "Program Files" / "nodejs" / "npm.CMD")
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    (tmp_path / ".env.example").write_text("DOCINTEL_PROVIDER_MODE=tesseract\n")
    monkeypatch.setattr(dev.shutil, "which", lambda name: launcher if name == "npm" else name)
    calls = []

    def windows_run(argv, **kwargs):
        if argv[0] == "npm":
            raise FileNotFoundError(2, "Bare npm cannot launch the Windows command shim")
        assert isinstance(argv, list)
        assert not kwargs.get("shell", False)
        assert kwargs["cwd"] == tmp_path and kwargs["check"] is True
        calls.append(argv)

    monkeypatch.setattr(dev.subprocess, "run", windows_run)
    monkeypatch.setattr("sys.argv", ["dev.py", task])
    dev.main()
    npm_calls = [args for args in calls if args[0] == launcher]
    assert npm_calls
    assert all(args[1:3] == ["--prefix", "frontend"] for args in npm_calls)
    if task == "frontend-check":
        assert [args[4] for args in npm_calls] == [
            "contracts:check",
            "typecheck",
            "lint",
            "format:check",
            "test",
            "build",
        ]


def test_unix_executable_and_argument_boundaries_are_preserved(dev, tmp_path, monkeypatch):
    launcher = str(tmp_path / "tools with spaces" / "npm")
    monkeypatch.setattr(dev.shutil, "which", lambda _: launcher)
    called = []
    monkeypatch.setattr(dev.subprocess, "run", lambda argv, **kwargs: called.append((argv, kwargs)))
    command = ["npm", "--prefix", "frontend", "run", "test"]
    dev.run(command)
    assert command[0] == "npm"  # Shared command templates must stay reusable.
    assert len(called) == 1
    assert called[0][0] == [launcher, *command[1:]]
    assert called[0][1]["cwd"] == dev.ROOT and called[0][1]["check"] is True
    assert not called[0][1].get("shell", False)


def test_missing_executable_fails_before_subprocess(dev, monkeypatch):
    monkeypatch.setattr(dev.shutil, "which", lambda _: None)
    monkeypatch.setattr(
        dev.subprocess, "run", lambda *_a, **_k: pytest.fail("Unexpected subprocess")
    )
    with pytest.raises(FileNotFoundError, match="npm"):
        dev.run(["npm", "--version"])


def test_child_failure_retains_exit_code(dev, monkeypatch):
    monkeypatch.setattr(dev.shutil, "which", lambda name: "/tools/" + name)

    def fail(argv, **_):
        raise subprocess.CalledProcessError(23, argv)

    monkeypatch.setattr(dev.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError) as failed:
        dev.run(["npm", "--version"])
    assert failed.value.returncode == 23


@pytest.mark.parametrize("exit_code", [0, 23])
def test_relative_path_launcher_survives_child_cwd(dev, tmp_path, monkeypatch, exit_code):
    caller = tmp_path / "caller"
    tools = caller / "launcher tools"
    tools.mkdir(parents=True)
    root = tmp_path / "repo"
    root.mkdir()
    marker = tmp_path / "child cwd.txt"
    if os.name == "nt":
        launcher = tools / "npm.CMD"
        launcher.write_text(f'@echo off\ncd > "{marker}"\nexit /b {exit_code}\n')
        monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT;.CMD")
    else:
        launcher = tools / "npm"
        launcher.write_text(f'#!/bin/sh\npwd > "{marker}"\nexit {exit_code}\n')
        launcher.chmod(0o755)
    monkeypatch.chdir(caller)
    monkeypatch.setenv("PATH", "launcher tools")
    monkeypatch.setattr(dev, "ROOT", root)
    executable = dev.shutil.which("npm")
    assert executable is not None and not Path(executable).is_absolute()
    if exit_code:
        with pytest.raises(subprocess.CalledProcessError) as failed:
            dev.run(["npm", "--version"])
        assert failed.value.returncode == exit_code
    else:
        dev.run(["npm", "--version"])
    assert Path(marker.read_text().strip()).resolve() == root.resolve()
