import re

from .base import ToolResult, ToolWrapper

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_FOUND_RE = re.compile(r"\[\+\]\s+(\S+)")


class HoleheWrapper(ToolWrapper):
    """Email -> accounts in use. Parses the '[+]' lines from stdout."""

    name = "holehe"
    binary = "holehe"

    def _args(self, target):
        return [target, "--only-used"]

    def _parse(self, target, proc):
        out = _ANSI_RE.sub("", proc.stdout or "")
        hits = [{"site": m.group(1), "url": ""} for m in _FOUND_RE.finditer(out)]
        return ToolResult(self.name, target, hits=hits, raw=out[:4000])
