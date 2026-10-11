"""Resolve the AI provider for a request: app-entered settings (per owner) override environment defaults."""
import ipaddress
import socket
from urllib.parse import urlparse

from app.config import Settings
from app.integrations.ai import ProviderUnavailable
from app.models import AiSetting
from app.services import secrets

PROVIDERS = ("mock", "claude", "openai_compatible")


class SettingsError(ValueError):
    pass


def _is_loopback_host(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1")


def validate_base_url(url: str, is_demo: bool) -> str:
    """https only. Demo may use http to a loopback host (e.g. a local model server).
    Live mode additionally rejects hosts that resolve to private/loopback/link-local addresses (SSRF guard)."""
    url = url.strip().rstrip("/")
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise SettingsError("Base URL must look like https://host/path (no credentials in the URL).")
    host = p.hostname.lower()
    if p.scheme == "http" and not (is_demo and _is_loopback_host(host)):
        raise SettingsError("Base URL must use https (http is only allowed for localhost in demo mode).")
    if not is_demo or not _is_loopback_host(host):
        try:
            infos = socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            if not is_demo:
                raise SettingsError("Base URL host could not be resolved.")
            infos = []
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if not is_demo and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                raise SettingsError("Base URL must not point to a private or local network address.")
    return url


def clean_key(raw: str) -> str:
    key = raw.strip()
    if len(key) < 8 or len(key) > 512 or any(c.isspace() for c in key) or not key.isprintable():
        raise SettingsError("That does not look like a valid API key.")
    return key


def effective_settings(settings: Settings, row: AiSetting | None) -> Settings:
    """Settings with the owner's app-entered provider applied. Raises ProviderUnavailable if the key can't be used."""
    if row is None:
        return settings
    if row.provider == "mock":
        return settings.model_copy(update={"ai_provider": "mock"})
    try:
        key = secrets.decrypt(settings, row.encrypted_key) if row.encrypted_key else ""
    except secrets.SecretsUnavailable as exc:
        raise ProviderUnavailable(str(exc))
    if row.provider == "claude":
        return settings.model_copy(update={"ai_provider": "claude", "anthropic_api_key": key, "claude_model": row.model or ""})
    return settings.model_copy(update={"ai_provider": "openai_compatible", "llm_api_key": key,
                                       "llm_base_url": row.base_url or "", "llm_model": row.model or ""})


def public_view(settings: Settings, row: AiSetting | None) -> dict:
    """Never includes the key; only whether one is configured and its last 4 characters."""
    from app.integrations.ai import ai_status
    try:
        eff = effective_settings(settings, row)
        status = ai_status(eff)
    except ProviderUnavailable as exc:
        status = {"provider": row.provider if row else settings.ai_provider, "available": False, "detail": str(exc)}
    source = "app" if row else ("env" if settings.ai_provider != "mock" else "none")
    return {
        "source": source,
        "provider": row.provider if row else settings.ai_provider,
        "base_url": row.base_url if row else (settings.llm_base_url or None),
        "model": row.model if row else (settings.claude_model or settings.llm_model or None),
        "key_configured": bool(row.encrypted_key) if row else bool(settings.anthropic_api_key or settings.llm_api_key),
        "key_last4": row.key_last4 if row else None,
        "available": status.get("available", False),
        "detail": status.get("detail"),
    }
