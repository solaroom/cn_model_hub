"""Public search API for repositories and namespaces."""

from fastapi import APIRouter, Depends, Query

from kohakuhub.auth.dependencies import get_optional_user
from kohakuhub.auth.permissions import RepoReadDeniedError, check_repo_read_permission
from kohakuhub.db import Repository, User

router = APIRouter()


def _repo_to_search_result(repo: Repository) -> dict:
    return {
        "id": repo.full_id,
        "type": repo.repo_type,
        "author": repo.namespace,
        "name": repo.name,
        "private": repo.private,
        "downloads": repo.downloads,
        "likes": repo.likes_count,
        "createdAt": repo.created_at.isoformat() if repo.created_at else None,
    }


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    repo_type: str | None = Query(
        None, pattern="^(model|dataset|space|all)$"
    ),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("relevance", pattern="^(relevance|recent|downloads|likes)$"),
    include_users: bool = Query(True),
    user: User | None = Depends(get_optional_user),
):
    """Search visible repositories and public namespaces."""
    query = q.strip()
    if not query:
        return {"query": q, "repositories": [], "users": []}

    repos_query = Repository.select().where(
        (Repository.full_id.contains(query))
        | (Repository.name.contains(query))
        | (Repository.namespace.contains(query))
    )

    if repo_type and repo_type != "all":
        repos_query = repos_query.where(Repository.repo_type == repo_type)

    if sort == "downloads":
        repos_query = repos_query.order_by(Repository.downloads.desc())
    elif sort == "likes":
        repos_query = repos_query.order_by(Repository.likes_count.desc())
    elif sort == "recent":
        repos_query = repos_query.order_by(Repository.created_at.desc())
    else:
        # Prefer exact/full-id matches, then keep newer results near the top.
        repos_query = repos_query.order_by(Repository.created_at.desc())

    repositories = []
    for repo in repos_query.limit(limit * 2):
        try:
            check_repo_read_permission(repo, user)
        except RepoReadDeniedError:
            continue
        repositories.append(_repo_to_search_result(repo))
        if len(repositories) >= limit:
            break

    users = []
    if include_users:
        user_query = (
            User.select()
            .where(
                (User.username.contains(query))
                | (User.full_name.contains(query))
                | (User.description.contains(query))
            )
            .order_by(User.created_at.desc())
            .limit(min(limit, 20))
        )
        users = [
            {
                "username": item.username,
                "name": item.full_name or item.username,
                "is_org": item.is_org,
                "bio": item.bio or item.description,
            }
            for item in user_query
        ]

    return {
        "query": query,
        "repositories": repositories,
        "users": users,
    }
