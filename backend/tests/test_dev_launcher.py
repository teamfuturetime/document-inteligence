"""Exercise the shared dev entry point without a shell or global tool changes."""

import importlib.util
import subprocess

import pytest

from docintel.config import ROOT


@pytest.fixture
def dev():
    spec = importlib.util.spec_from_file_location("dev_launcher", ROOT / "scripts/dev.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("task", ["setup", "frontend", "frontend-check", "e2e", "check"])
def test_windows_npm_entry_points_resolve_launcher(dev, tmp_path, monkeypatch, task):
    launcher = r"C:\Program Files\nodejs\npm.CMD"
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


def test_unix_executable_and_argument_boundaries_are_preserved(dev, monkeypatch):
    monkeypatch.setattr(dev.shutil, "which", lambda _: "/tools with spaces/npm")
    called = []
    monkeypatch.setattr(dev.subprocess, "run", lambda argv, **kwargs: called.append((argv, kwargs)))
    command = ["npm", "--prefix", "frontend", "run", "test"]
    dev.run(command)
    assert command[0] == "npm"  # Shared command templates must stay reusable.
    assert len(called) == 1
    assert called[0][0] == ["/tools with spaces/npm", *command[1:]]
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
