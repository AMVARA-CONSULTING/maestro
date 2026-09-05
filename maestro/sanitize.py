from __future__ import annotations

import re

_DISCORD_TOKEN_RE = re.compile(
    r"\bMT[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{10,}\b"
)
_KV_SECRET_RE = re.compile(
    r"(?im)(^|[;\s])("
    r"(?:api[_-]?key|client[_-]?secret|secret|token|password|passwd|"
    r"authorization|bearer|passphrase)"
    r"\s*[:=]\s*)(\S+)"
)
_BEARER_RE = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9._\-+/=]{20,})")
_ENV_ASSIGN_RE = re.compile(
    r"(?im)^(\s*(?:"
    r"DISCORD_TOKEN|DISCORD_BOT_TOKEN|DISCORD_PUBLIC_KEY|"
    r"OPENAI_API_KEY|REDMINE_API_KEY|LLM_API_KEY|"
    r"GH_TOKEN|GITHUB_TOKEN|AWS_SECRET_ACCESS_KEY|"
    r"MAESTRO_[A-Z_]*TOKEN|TOR_[A-Z_]*TOKEN|"
    r"[A-Z][A-Z0-9_]*(?:_TOKEN|_SECRET|_PASSWORD|_PASS|_API_KEY|_PRIVATE_KEY)"
    r")\s*=\s*)(.+)$"
)
_SSH_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:OPENSSH|RSA|EC|DSA|ENCRYPTED) PRIVATE KEY-----[\s\S]*?"
    r"-----END (?:OPENSSH|RSA|EC|DSA|ENCRYPTED) PRIVATE KEY-----"
)
_REDACT = "[REDACTED]"


def _redact_known_literals(text: str, literals: list[str]) -> str:
    out = text
    for val in literals:
        v = val.strip()
        if len(v) >= 8:
            out = out.replace(v, _REDACT)
    return out


def sanitize_for_discord(text: str, *, secret_literals: list[str] | None = None) -> str:
    if not text:
        return text
    out = _redact_known_literals(text, list(secret_literals or []))
    out = _DISCORD_TOKEN_RE.sub(_REDACT, out)
    out = _KV_SECRET_RE.sub(rf"\1\2{_REDACT}", out)
    out = _BEARER_RE.sub(rf"\1{_REDACT}", out)
    out = _ENV_ASSIGN_RE.sub(rf"\1{_REDACT}", out)
    out = _SSH_PRIVATE_KEY_RE.sub(_REDACT, out)
    return out


def chunk_discord(text: str, limit: int = 1900) -> list[str]:
    text = text.strip() or "(empty)"
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts
