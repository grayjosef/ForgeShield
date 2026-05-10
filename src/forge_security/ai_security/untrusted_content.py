"""D6 untrusted-content envelope.

Wraps externally-sourced text in an explicit untrusted envelope before it
is allowed anywhere near a model prompt. The wrapper:

* strips Unicode "format" (Cf) and "control" (Cc) categories that would
  otherwise let an attacker hide bytes (RTL overrides, BOMs, zero-width
  joiners, BEL) inside what looks like normal prose,
* neutralizes well-known prompt-injection lead-ins by replacing them
  with a visible bracketed token so reviewers and the model both see
  the neutralization rather than wondering why text disappeared,
* truncates pathologically long payloads with a literal sentinel,
* escapes the source attribute so a hostile source string cannot close
  the envelope tag, and
* emits a single XML-ish envelope that is trivial to grep for.

Scope: this is part of the ForgeShield scratch gate (FS-0.5). It does
NOT claim to defeat every prompt-injection attack. Its job is to give
the rest of the system one canonical, reviewable choke point for
external bytes.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Tuple

MAX_CONTENT_LEN = 8000
TRUNCATION_MARKER = "[CONTENT TRUNCATED FOR SAFETY]"

# (pattern, replacement) pairs. Patterns are case-insensitive where the
# upstream attacker payload commonly varies casing. Replacements are
# bracketed sentinels so neutralization is visible to humans reviewing
# logs and to the model itself.
_INJECTION_PATTERNS: Tuple[Tuple["re.Pattern[str]", str], ...] = (
    (re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
     "[NEUTRALIZED:ignore-previous]"),
    (re.compile(r"disregard\s+previous\s+instructions", re.IGNORECASE),
     "[NEUTRALIZED:disregard-previous]"),
    (re.compile(r"system\s+prompt", re.IGNORECASE),
     "[NEUTRALIZED:system-prompt]"),
    (re.compile(r"developer\s+message", re.IGNORECASE),
     "[NEUTRALIZED:developer-message]"),
    (re.compile(r"reveal\s+hidden\s+instructions", re.IGNORECASE),
     "[NEUTRALIZED:reveal-hidden]"),
    # ChatML markers. Case-sensitive: these are a fixed wire format.
    (re.compile(r"<\|system\|>"), "[NEUTRALIZED:chatml-system]"),
    (re.compile(r"<\|assistant\|>"), "[NEUTRALIZED:chatml-assistant]"),
    (re.compile(r"<\|user\|>"), "[NEUTRALIZED:chatml-user]"),
    (re.compile(r"<\|im_start\|>"), "[NEUTRALIZED:chatml-im-start]"),
    (re.compile(r"<\|im_end\|>"), "[NEUTRALIZED:chatml-im-end]"),
    # Newline-prefixed role-switch markers (Anthropic / generic).
    (re.compile(r"\nHuman:\s*", re.IGNORECASE),
     "\n[NEUTRALIZED:role-human] "),
    (re.compile(r"\nAssistant:\s*", re.IGNORECASE),
     "\n[NEUTRALIZED:role-assistant] "),
    (re.compile(r"\nSystem:\s*", re.IGNORECASE),
     "\n[NEUTRALIZED:role-system] "),
    (re.compile(r"BEGIN\s+SYSTEM", re.IGNORECASE),
     "[NEUTRALIZED:begin-system]"),
)


def _strip_dangerous_unicode(text: str) -> str:
    """Remove Cf (format) and Cc (control) Unicode characters.

    Whitespace that callers and pattern-matchers depend on is preserved:
    newline and tab are kept even though they are technically Cc, because
    the role-switch patterns above key off "\n" and an attacker can't
    smuggle anything dangerous through a plain newline.
    """
    out: list[str] = []
    for ch in text:
        if ch in ("\n", "\t"):
            out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Cc"):
            continue
        out.append(ch)
    return "".join(out)


def _sanitize_source(source: str) -> str:
    """Escape characters that could break out of the envelope attribute.

    Quotes and angle brackets are the only real danger inside an
    attribute value; we also flatten newlines so a multi-line source
    string cannot terminate the opening tag.
    """
    cleaned = _strip_dangerous_unicode(source)
    return (
        cleaned.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def wrap_untrusted_content(content: str, source: str) -> str:
    """Return ``content`` wrapped in an external-untrusted envelope.

    Order of operations matters: dangerous Unicode is stripped BEFORE
    the injection-pattern replacements, so an attacker cannot hide a
    marker inside zero-width joiners. Truncation runs after pattern
    replacement so neutralization tokens are not chopped in half.
    """
    if not isinstance(content, str):
        raise TypeError("content must be str")
    if not isinstance(source, str):
        raise TypeError("source must be str")

    cleaned = _strip_dangerous_unicode(content)
    for pattern, replacement in _INJECTION_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)

    truncated = False
    if len(cleaned) > MAX_CONTENT_LEN:
        cleaned = cleaned[:MAX_CONTENT_LEN]
        truncated = True

    if truncated:
        cleaned = cleaned + "\n" + TRUNCATION_MARKER

    safe_source = _sanitize_source(source)
    return (
        f'<EXTERNAL_UNTRUSTED_CONTENT source="{safe_source}" '
        f'trust="none" origin="external">\n'
        f"{cleaned}\n"
        f"</EXTERNAL_UNTRUSTED_CONTENT>"
    )


__all__ = [
    "wrap_untrusted_content",
    "MAX_CONTENT_LEN",
    "TRUNCATION_MARKER",
]
