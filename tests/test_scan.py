from test_api import client as client
from test_api import finish, save


def test_scan_verifies_originals_and_reuses_single_entry_extractions(client):
    for text in ["Nobody heard me at dinner.", "A cup in a meadow.", "The phone would not dial."]:
        save(client, text)
    calls = []
    provider = client.app.state.providers["codex"]
    run = provider.run

    async def observed(request, directory):
        calls.append(request.task)
        return await run(request, directory)

    provider.run = observed
    first = client.post("/api/scan", json={"provider": "codex"}).json()
    assert finish(client, first["id"])["state"] == "completed"
    assert calls.count("extract") == 3
    assert any(n["kind"] == "theme" for n in client.get("/api/graph").json()["nodes"])
    calls.clear()
    second = client.post("/api/scan", json={"provider": "codex"}).json()
    assert finish(client, second["id"])["state"] == "completed"
    assert calls == ["group", "connect"]
