"""Subprocess-Wrapper fuer externe OSINT-CLI-Tools (availability-gated)."""

from .base import ToolResult, ToolWrapper
from .holehe import HoleheWrapper
from .maigret import MaigretWrapper

USERNAME_TOOLS = [MaigretWrapper]
EMAIL_TOOLS = [HoleheWrapper]

__all__ = [
    "ToolResult",
    "ToolWrapper",
    "HoleheWrapper",
    "MaigretWrapper",
    "USERNAME_TOOLS",
    "EMAIL_TOOLS",
]
