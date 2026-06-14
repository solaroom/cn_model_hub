"""API tests for repository discussions."""


async def test_create_discussion_and_comment(owner_client):
    create_response = await owner_client.post(
        "/api/models/owner/demo-model/discussions",
        json={
            "title": "中文评测结果讨论",
            "body": "这个模型在中文问答任务上需要补充更多测试样例。",
        },
    )
    create_response.raise_for_status()
    discussion = create_response.json()
    assert discussion["title"] == "中文评测结果讨论"
    assert discussion["author"]["username"] == "owner"

    list_response = await owner_client.get("/api/models/owner/demo-model/discussions")
    list_response.raise_for_status()
    assert any(
        item["id"] == discussion["id"]
        for item in list_response.json()["discussions"]
    )

    comment_response = await owner_client.post(
        f"/api/models/owner/demo-model/discussions/{discussion['id']}/comments",
        json={"body": "可以先加入 C-Eval 和 CMMLU 的人工录入结果。"},
    )
    comment_response.raise_for_status()
    assert comment_response.json()["author"]["username"] == "owner"

    detail_response = await owner_client.get(
        f"/api/models/owner/demo-model/discussions/{discussion['id']}"
    )
    detail_response.raise_for_status()
    payload = detail_response.json()
    assert payload["discussion"]["id"] == discussion["id"]
    assert len(payload["comments"]) == 1


async def test_discussion_delete_requires_author_or_repo_writer(
    owner_client, outsider_client
):
    create_response = await owner_client.post(
        "/api/models/owner/demo-model/discussions",
        json={"title": "删除权限测试", "body": "只有作者或维护者可以删除。"},
    )
    create_response.raise_for_status()
    discussion_id = create_response.json()["id"]

    forbidden = await outsider_client.delete(
        f"/api/models/owner/demo-model/discussions/{discussion_id}"
    )
    assert forbidden.status_code == 403

    deleted = await owner_client.delete(
        f"/api/models/owner/demo-model/discussions/{discussion_id}"
    )
    deleted.raise_for_status()
    assert deleted.json()["success"] is True
