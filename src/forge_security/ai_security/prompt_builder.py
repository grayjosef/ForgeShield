"""D7 PromptBuilder -- five-layer prompt assembly.

Goal: make it physically harder for any caller to interleave external
content with system instructions. There is one, and only one, method
that accepts external bytes: ``add_external_content``. That method is
the only path that calls ``wrap_untrusted_content``.

Layers (always emitted in this order):

  1. system instructions
  2. developer constraints
  3. trusted internal context
  4. external untrusted content (wrapped)
  5. user task

System / developer / trusted layers reject role-switching markers
outright via :class:`PromptInjectionError` so an attacker who controls
a config file cannot smuggle a fake role boundary into the trusted
section. External content is neutralized rather than rejected, because
the envelope's whole point is to safely accept hostile bytes.

``build()`` returns ``list[dict]`` so callers can index by integer
position (``messages[0]["role"]``) per the FS scratch-gate D3/CC-10
requirement. Dict-style ``messages["role"]`` keying is intentionally
not supported.
"""
from __future__ import annotations

import re
from typing import List

from .untrusted_content import wrap_untrusted_content

_FORBIDDEN_SYSTEM_MARKERS = (
    re.compile(r"<\|system\|>"),
    re.compile(r"<\|assistant\|>"),
    re.compile(r"<\|user\|>"),
    re.compile(r"<\|im_start\|>"),
    re.compile(r"<\|im_end\|>"),
    re.compile(r"\nHuman:", re.IGNORECASE),
    re.compile(r"\nAssistant:", re.IGNORECASE),
    re.compile(r"\nSystem:", re.IGNORECASE),
    re.compile(r"BEGIN\s+SYSTEM", re.IGNORECASE),
)


class PromptInjectionError(ValueError):
    """Raised when a trusted layer is given content that looks hostile."""


def _reject_role_markers(label: str, text: str) -> None:
    for pat in _FORBIDDEN_SYSTEM_MARKERS:
        if pat.search(text):
            raise PromptInjectionError(
                f"role-switching marker detected in {label} layer; "
                f"external content must go through add_external_content()"
            )


class PromptBuilder:
    """Assemble a five-layer message list with one external choke point."""

    def __init__(self) -> None:
        self._system: List[str] = []
        self._developer: List[str] = []
        self._trusted: List[str] = []
        self._external: List[str] = []
        self._user: List[str] = []

    def add_system_instruction(self, text: str) -> "PromptBuilder":
        if not isinstance(text, str):
            raise TypeError("system instruction must be str")
        _reject_role_markers("system", text)
        self._system.append(text)
        return self

    def add_developer_constraint(self, text: str) -> "PromptBuilder":
        if not isinstance(text, str):
            raise TypeError("developer constraint must be str")
        _reject_role_markers("developer", text)
        self._developer.append(text)
        return self

    def add_trusted_context(self, text: str) -> "PromptBuilder":
        if not isinstance(text, str):
            raise TypeError("trusted context must be str")
        _reject_role_markers("trusted", text)
        self._trusted.append(text)
        return self

    def add_external_content(self, content: str, source: str) -> "PromptBuilder":
        """The ONLY sanctioned path for external bytes.

        Routes through :func:`wrap_untrusted_content`, so callers cannot
        bypass the envelope by passing pre-wrapped strings or by
        formatting external bytes into a system instruction.
        """
        wrapped = wrap_untrusted_content(content, source)
        self._external.append(wrapped)
        return self

    def add_user_task(self, text: str) -> "PromptBuilder":
        if not isinstance(text, str):
            raise TypeError("user task must be str")
        self._user.append(text)
        return self

    def build(self) -> List[dict]:
        messages: List[dict] = []
        if self._system:
            messages.append(
                {"role": "system", "content": "\n\n".join(self._system)}
            )
        if self._developer:
            messages.append(
                {"role": "system",
                 "content": "[developer]\n" + "\n\n".join(self._developer)}
            )
        if self._trusted:
            messages.append(
                {"role": "system",
                 "content": "[trusted-context]\n" + "\n\n".join(self._trusted)}
            )
        if self._external:
            messages.append(
                {"role": "user", "content": "\n\n".join(self._external)}
            )
        if self._user:
            messages.append(
                {"role": "user", "content": "\n\n".join(self._user)}
            )
        return messages


__all__ = ["PromptBuilder", "PromptInjectionError"]
