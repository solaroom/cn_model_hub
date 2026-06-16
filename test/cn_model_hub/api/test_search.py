"""API tests for public search."""


async def test_search_finds_visible_repository(client):
    response = await client.get(
        "/api/search",
        params={"q": "demo-model", "repo_type": "model", "limit": 10},
    )
    response.raise_for_status()
    payload = response.json()
    assert any(
        repo["id"] == "owner/demo-model" for repo in payload["repositories"]
    )


async def test_search_hides_private_repository_without_access(client, owner_client):
    hidden_response = await client.get(
        "/api/search",
        params={"q": "private-dataset", "repo_type": "dataset", "limit": 10},
    )
    hidden_response.raise_for_status()
    assert all(
        repo["id"] != "acme-labs/private-dataset"
        for repo in hidden_response.json()["repositories"]
    )

    visible_response = await owner_client.get(
        "/api/search",
        params={"q": "private-dataset", "repo_type": "dataset", "limit": 10},
    )
    visible_response.raise_for_status()
    assert any(
        repo["id"] == "acme-labs/private-dataset"
        for repo in visible_response.json()["repositories"]
    )
