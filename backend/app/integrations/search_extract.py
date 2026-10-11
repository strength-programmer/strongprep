"""Tavily (find pages) and Firecrawl (read pages) adapter interfaces.

First build: deterministic mock responses only. Live adapters are intentionally not implemented:
live search/scraping needs an approved source and access method first (spec sections 0 and 14).
Fetched page text is untrusted data and must never carry instructions to the app.
"""
from typing import Protocol

from app.config import get_settings


class IntegrationUnavailable(Exception):
    pass


class SearchProvider(Protocol):
    name: str

    def search(self, query: str) -> list[dict]: ...


class ExtractionProvider(Protocol):
    name: str

    def extract(self, url: str) -> dict: ...


class MockSearch:
    name = "mock"

    def search(self, query: str) -> list[dict]:
        return [{"title": "Fictional Harbor Strongman Open (mock result)", "url": "fixture://harbor-open",
                 "note": "Deterministic mock; not a real search result."}]


class MockExtraction:
    name = "mock"

    def extract(self, url: str) -> dict:
        return {"url": url, "proposed_fields": {}, "note": "Mock extraction returns no fields. Use manual entry."}


class TavilySearch:
    name = "tavily"

    def search(self, query: str) -> list[dict]:
        raise IntegrationUnavailable("Live Tavily search is a later milestone and is not implemented.")


class FirecrawlExtraction:
    name = "firecrawl"

    def extract(self, url: str) -> dict:
        raise IntegrationUnavailable("Live Firecrawl extraction is a later milestone and is not implemented.")


def integration_status() -> dict:
    s = get_settings()
    return {
        "tavily": {"configured": bool(s.tavily_api_key), "live_adapter": False, "active": "mock"},
        "firecrawl": {"configured": bool(s.firecrawl_api_key), "live_adapter": False, "active": "mock"},
    }
