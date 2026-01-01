import os
import subprocess
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExecResult:
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        if self.stderr:
            return f"{self.stdout}{self.stderr}"
        return self.stdout


def _docker_exec(command: List[str], timeout_s: Optional[int] = None) -> ExecResult:
    container = "attacker"
    proc = subprocess.Popen(
        ["docker", "exec", container] + command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    stdout_parts: List[str] = []

    def _reader() -> None:
        if proc.stdout is None:
            return
        try:
            for line in proc.stdout:
                stdout_parts.append(line)
        except Exception:
            return

    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_parts.append("[timeout]\n")
    finally:
        if proc.stdout is not None:
            try:
                proc.stdout.close()
            except Exception:
                pass
        t.join(timeout=1)

    return ExecResult(
        command=["docker", "exec", container] + command,
        exit_code=proc.returncode if proc.returncode is not None else 1,
        stdout="".join(stdout_parts),
        stderr="",
    )


def run_recon_nmap() -> ExecResult:
    timeout_s = int(os.getenv("RECON_NMAP_TIMEOUT_S", "300"))
    nmap_cmd = ["nmap", "-sV", "--version-light", "-Pn", "--open", "-T4", "victim"]
    return _docker_exec(nmap_cmd, timeout_s=timeout_s)
