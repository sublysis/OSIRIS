import glob
import json
import os
import subprocess
import tempfile

from .base import ToolResult, ToolWrapper


class MaigretWrapper(ToolWrapper):
    """Username -> accounts on many platforms. Writes a JSON report to a temp directory.

    Flags may vary depending on the maigret version; raw stdout is kept as well.
    """

    name = "maigret"
    binary = "maigret"

    def run(self, target, timeout=240):
        if not self.available():
            return ToolResult(self.name, target, available=False, error=f"{self.binary} not installed")
        folder = tempfile.mkdtemp(prefix="maigret_")
        try:
            proc = subprocess.run(
                [self.binary, target, "--no-progressbar", "--timeout", "20",
                 "--json", "simple", "--folderoutput", folder],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(self.name, target, error="Timeout")
        except Exception as e:
            return ToolResult(self.name, target, error=str(e))

        hits = self._parse_reports(folder)
        return ToolResult(self.name, target, hits=hits, raw=(proc.stdout or "")[:4000])

    def _parse_reports(self, folder):
        hits = []
        for path in glob.glob(os.path.join(folder, "*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            for site, info in data.items():
                if not isinstance(info, dict):
                    continue
                status = (info.get("status") or {}).get("status")
                url = info.get("url_user") or info.get("url")
                if status == "Claimed" and url:
                    hits.append({"site": site, "url": url})
        return hits
