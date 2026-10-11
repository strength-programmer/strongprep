import json
from datetime import date

import httpx
import pytest
from cryptography.fernet import Fernet

from app.config import Settings
from app.integrations.ai import OpenAICompatiblePlanProvider
from app.models import AiSetting
from app.services import ai_settings as svc
from app.services import secrets
from tests.conftest import auth, make_client
from tests.test_api import run_journey

KEY = "sk-super-secret-key-1234"
BODY = {"provider": "openai_compatible", "base_url": "https://llm.example/v1", "model": "qwen-test", "api_key": KEY}


@pytest.fixture(autouse=True)
def _no_dns(monkeypatch):
    """Keep tests offline: resolve every host to a public address unless a test overrides it."""
    monkeypatch.setattr(svc.socket, "getaddrinfo", lambda host, *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    monkeypatch.setattr(OpenAICompatiblePlanProvider, "_default_transport", None)


def raw_rows(Session):
    with Session() as db:
        return [(r.owner_id, r.provider, r.encrypted_key, r.key_last4) for r in db.query(AiSetting)]


def test_key_is_encrypted_masked_and_never_returned(demo):
    client, Session, path, s = demo
    r = client.put("/ai-settings", json=BODY)
    assert r.status_code == 200, r.text
    for text in (r.text, client.get("/ai-settings").text, client.get("/status").text, client.get("/export").text):
        assert KEY not in text and "super-secret" not in text
    v = client.get("/ai-settings").json()
    assert v["key_configured"] is True and v["key_last4"] == "1234" and v["source"] == "app" and v["available"] is True
    (owner, provider, enc, last4), = raw_rows(Session)
    assert enc and KEY not in enc and secrets.decrypt(s, enc) == KEY


def test_status_and_plan_use_the_in_app_key(demo_athlete):
    client, Session, path, s = demo_athlete
    seen = {}
    plan_holder = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(plan_holder["plan"])}}]})

    # build a valid plan once using the mock path, then have the "LLM" return it
    *_, mock_plan = run_journey(client)
    plan_holder["plan"] = {k: v for k, v in mock_plan["content"].items() if k not in ("provider", "ai_label", "template_notice", "validation")}
    OpenAICompatiblePlanProvider._default_transport = httpx.MockTransport(handler)

    assert client.get("/status").json()["ai"]["provider"] == "mock"
    assert client.put("/ai-settings", json=BODY).status_code == 200
    st = client.get("/status").json()["ai"]
    assert st["provider"] == "openai_compatible" and st["available"] and KEY not in json.dumps(st)

    a = client.get("/assessments").json()[0]
    r = client.post("/preparation-plans", json={"assessment_id": a["id"]})
    assert r.status_code == 201, r.text
    assert r.json()["provider"] == "openai_compatible" and "qwen-test" in r.json()["content"]["ai_label"]
    assert seen["auth"] == f"Bearer {KEY}" and seen["url"] == "https://llm.example/v1/chat/completions"

    # removing the key reverts to the environment default (mock)
    assert client.delete("/ai-settings").status_code == 204
    assert client.get("/status").json()["ai"]["provider"] == "mock"
    assert client.post("/preparation-plans", json={"assessment_id": a["id"]}).json()["provider"] == "mock"


def test_update_without_key_keeps_stored_key_but_provider_change_requires_new_key(demo):
    client, Session, *_ = demo
    client.put("/ai-settings", json=BODY)
    r = client.put("/ai-settings", json={**{k: v for k, v in BODY.items() if k != "api_key"}, "model": "qwen-other"})
    assert r.status_code == 200 and r.json()["model"] == "qwen-other" and r.json()["key_last4"] == "1234"
    r = client.put("/ai-settings", json={"provider": "claude", "model": "some-claude-model"})
    assert r.status_code == 422 and "API key" in r.json()["detail"]
    assert client.put("/ai-settings", json={"provider": "mock"}).json()["key_configured"] is False
    assert raw_rows(Session)[0][2] is None  # key wiped when switching to mock


@pytest.mark.parametrize("body,fragment", [
    ({**BODY, "api_key": "short"}, "valid API key"),
    ({**BODY, "api_key": "has space in it key"}, "valid API key"),
    ({**BODY, "model": " "}, "model name"),
    ({**BODY, "base_url": ""}, "Base URL"),
    ({**BODY, "base_url": "http://llm.example/v1"}, "https"),
    ({**BODY, "base_url": "https://user:pw@llm.example/v1"}, "credentials"),
    ({**BODY, "base_url": "ftp://llm.example"}, "Base URL"),
])
def test_validation(demo, body, fragment):
    client, *_ = demo
    r = client.put("/ai-settings", json=body)
    assert r.status_code == 422 and fragment in r.json()["detail"]
    assert KEY not in r.text


def test_demo_allows_http_only_for_loopback(demo):
    client, *_ = demo
    assert client.put("/ai-settings", json={**BODY, "base_url": "http://localhost:11434/v1"}).status_code == 200
    assert client.put("/ai-settings", json={**BODY, "base_url": "http://127.0.0.1:8080/v1"}).status_code == 200
    assert client.put("/ai-settings", json={**BODY, "base_url": "http://192.168.1.5:8080/v1"}).status_code == 422


def test_live_mode_blocks_private_addresses_and_needs_secret(live, monkeypatch):
    client, Session, s = live
    H = auth("user-a")
    for ip in ("10.0.0.5", "127.0.0.1", "169.254.169.254", "192.168.0.1", "::1"):
        monkeypatch.setattr(svc.socket, "getaddrinfo", lambda host, *a, ip=ip, **k: [(2, 1, 6, "", (ip, 443))])
        r = client.put("/ai-settings", json=BODY, headers=H)
        assert r.status_code == 422 and "private or local" in r.json()["detail"], ip
    assert client.put("/ai-settings", json={**BODY, "base_url": "https://localhost/v1"}, headers=H).status_code == 422
    monkeypatch.setattr(svc.socket, "getaddrinfo", lambda host, *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    assert client.put("/ai-settings", json=BODY, headers=H).status_code == 200

    # live without APP_SECRET_KEY cannot store keys
    s2 = Settings(app_mode="live", database_url="sqlite:///x.db", supabase_url=s.supabase_url, supabase_jwt_secret=s.supabase_jwt_secret)
    client.app.dependency_overrides[__import__("app.config", fromlist=["get_settings"]).get_settings] = lambda: s2
    r = client.put("/ai-settings", json={**BODY, "model": "m2"}, headers=H)
    assert r.status_code == 503 and "APP_SECRET_KEY" in r.json()["detail"]


def test_live_settings_are_per_account(live):
    client, Session, s = live
    A, B = auth("user-a"), auth("user-b")
    assert client.put("/ai-settings", json=BODY, headers=A).status_code == 200
    assert client.get("/ai-settings", headers=B).json()["key_configured"] is False
    assert client.get("/status", headers=B).json()["ai"]["provider"] == "mock"
    assert client.get("/status", headers=A).json()["ai"]["provider"] == "openai_compatible"
    assert client.post("/ai-settings/test", headers=B).json()["message"].startswith("Mock")
    assert client.delete("/ai-settings", headers=B).status_code == 204
    assert client.get("/ai-settings", headers=A).json()["key_configured"] is True
    for h in ({}, {"Authorization": "Bearer junk"}):
        assert client.get("/ai-settings", headers=h).status_code == 401
        assert client.put("/ai-settings", json=BODY, headers=h).status_code == 401
        assert client.delete("/ai-settings", headers=h).status_code == 401
    assert client.get("/status", headers={"Authorization": "Bearer junk"}).status_code == 200  # tolerant, no AI row used
    # deleting all account data removes the stored key too
    assert client.delete("/my-data", headers=A).status_code == 204
    assert raw_rows(Session) == []


def test_connection_test_reports_without_leaking(demo):
    client, *_ = demo
    assert client.post("/ai-settings/test").json() == {"ok": True, "message": "Mock AI needs no key."}
    client.put("/ai-settings", json=BODY)
    cases = [(httpx.Response(200, json={"choices": []}), True, "responded"),
             (httpx.Response(401, text=f"bad key {KEY}"), False, "rejected the API key"),
             (httpx.Response(404, text="x"), False, "404"),
             (httpx.Response(500, text=KEY), False, "HTTP 500")]
    for resp, ok, text in cases:
        OpenAICompatiblePlanProvider._default_transport = httpx.MockTransport(lambda r, resp=resp: resp)
        out = client.post("/ai-settings/test").json()
        assert out["ok"] is ok and text in out["message"] and KEY not in json.dumps(out)

    def boom(request):
        raise httpx.ConnectError(f"cannot connect with {KEY}")
    OpenAICompatiblePlanProvider._default_transport = httpx.MockTransport(boom)
    out = client.post("/ai-settings/test").json()
    assert out == {"ok": False, "message": "Request failed: ConnectError."}


def test_undecryptable_key_gives_clear_unavailable_not_a_crash(demo_athlete):
    client, Session, path, s = demo_athlete
    client.put("/ai-settings", json=BODY)
    with Session() as db:  # simulate a rotated APP_SECRET_KEY
        row = db.query(AiSetting).first()
        row.encrypted_key = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
        db.commit()
    v = client.get("/ai-settings").json()
    assert v["available"] is False and "cannot be decrypted" in v["detail"]
    full = next(c for c in client.get("/competitions").json() if c["title"].startswith("Harbor"))
    a = client.post("/assessments", json={"competition_id": full["id"], "division_id": full["divisions"][0]["id"]}).json()
    r = client.post("/preparation-plans", json={"assessment_id": a["id"]})
    assert r.status_code == 503 and "decrypted" in r.json()["detail"]["message"]


def test_demo_generates_and_reuses_a_local_secret_file(tmp_path, monkeypatch):
    monkeypatch.setattr(secrets, "SECRET_FILE", tmp_path / ".strongprep-secret")
    s = Settings(app_mode="demo", database_url="sqlite:///x.db")
    token = secrets.encrypt(s, "abc12345")
    assert (tmp_path / ".strongprep-secret").exists()
    assert secrets.decrypt(s, token) == "abc12345"
    with pytest.raises(secrets.SecretsUnavailable):
        secrets.encrypt(Settings(app_mode="live", supabase_url="https://x"), "k")
    with pytest.raises(secrets.SecretsUnavailable):
        secrets.encrypt(Settings(app_mode="demo", app_secret_key="not-a-fernet-key"), "k")
