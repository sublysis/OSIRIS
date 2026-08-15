import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    tool: str
    target: str
    hits: list = field(default_factory=list)  # [{"site":.., "url":..}]
    raw: str = ""
    error: str | None = None
    available: bool = True


class ToolWrapper:
    """Base for external OSINT CLI tools. Skipped gracefully if the binary is missing."""

    name = "tool"
    binary = "tool"

    def available(self):
        return shutil.which(self.binary) is not None

    def run(self, target, timeout=180):
        if not self.available():
            return ToolResult(self.name, target, available=False, error=f"{self.binary} not installed")
        try:
            proc = subprocess.run(
                [self.binary, *self._args(target)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(self.name, target, error="Timeout")
        except Exception as e:  # OSError etc.
            return ToolResult(self.name, target, error=str(e))
        return self._parse(target, proc)

    def _args(self, target):
        raise NotImplementedError

    def _parse(self, target, proc):
        raise NotImplementedError
