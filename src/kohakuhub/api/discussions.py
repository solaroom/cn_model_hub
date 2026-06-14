"""Repository discussions API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from kohakuhub.auth.dependencies import get_current_user, get_optional_user
from kohakuhub.auth.permissions import (
    check_repo_read_permission,
    check_repo_write_permission,
)
from kohakuhub.db import Discussion, DiscussionComment, Repository, User, db
from kohakuhub.db_operations import get_repository

router = APIRouter()


class DiscussionCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    body: str = Field(..., min_length=1, max_length=20000)


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=12000)


def _now():
    return datetime.now(timezone.utc)


def _author_payload(author: User | None) -> dict:
    if not author:
        return {
            "username": "deleted-user",
            "name": "已删除用户",
            "avatarUrl": None,
        }

    return {
        "username": author.username,
        "name": author.full_name or author.username,
        "avatarUrl": f"/api/users/{author.username}/avatar",
    }


def _discussion_payload(discussion: Discussion, include_body: bool = True) -> dict:
    comment_count = (
        DiscussionComment.select()
        .where(DiscussionComment.discussion == discussion)
        .count()
    )
    data = {
        "id": discussion.id,
        "title": discussion.title,
        "author": _author_payload(discussion.author),
        "commentCount": comment_count,
        "createdAt": discussion.created_at.isoformat()
        if discussion.created_at
        else None,
        "updatedAt": discussion.updated_at.isoformat()
        if discussion.updated_at
        else None,
    }
    if include_body:
        data["body"] = discussion.body
    return data


def _comment_payload(comment: DiscussionComment) -> dict:
    return {
        "id": comment.id,
        "body": comment.body,
        "author": _author_payload(comment.author),
        "createdAt": comment.created_at.isoformat() if comment.created_at else None,
        "updatedAt": comment.updated_at.isoformat() if comment.updated_at else None,
    }


def _get_visible_repo(
    repo_type: str, namespace: str, name: str, user: User | None
) -> Repository:
    if repo_type not in {"model", "dataset", "space"}:
        raise HTTPException(400, detail={"error": "Invalid repository type"})

    repo = get_repository(repo_type, namespace, name)
    if not repo:
        raise HTTPException(404, detail={"error": "Repository not found"})

    check_repo_read_permission(repo, user)
    return repo


def _can_manage_repo_item(repo: Repository, user: User, author_id: int | None) -> bool:
    if author_id and author_id == user.id:
        return True
    try:
        check_repo_write_permission(repo, user)
        return True
    except HTTPException:
        return False


@router.get("/{repo_type}s/{namespace}/{name}/discussions")
async def list_discussions(
    repo_type: str,
    namespace: str,
    name: str,
    limit: int = Query(20, ge=1, le=100),
    user: User | None = Depends(get_optional_user),
):
    """List discussion threads for a repository."""
    repo = _get_visible_repo(repo_type, namespace, name, user)
    discussions = (
        Discussion.select()
        .where(Discussion.repository == repo)
        .order_by(Discussion.updated_at.desc(), Discussion.created_at.desc())
        .limit(limit)
    )

    return {
        "discussions": [
            _discussion_payload(discussion, include_body=False)
            for discussion in discussions
        ]
    }


@router.post("/{repo_type}s/{namespace}/{name}/discussions")
async def create_discussion(
    repo_type: str,
    namespace: str,
    name: str,
    payload: DiscussionCreate,
    user: User = Depends(get_current_user),
):
    """Create a discussion thread for a repository."""
    repo = _get_visible_repo(repo_type, namespace, name, user)
    title = payload.title.strip()
    body = payload.body.strip()
    if not title or not body:
        raise HTTPException(400, detail={"error": "Title and body are required"})

    discussion = Discussion.create(
        repository=repo,
        author=user,
        title=title,
        body=body,
        created_at=_now(),
        updated_at=_now(),
    )

    return _discussion_payload(discussion)


@router.get("/{repo_type}s/{namespace}/{name}/discussions/{discussion_id}")
async def get_discussion(
    repo_type: str,
    namespace: str,
    name: str,
    discussion_id: int,
    user: User | None = Depends(get_optional_user),
):
    """Get a discussion thread and its comments."""
    repo = _get_visible_repo(repo_type, namespace, name, user)
    discussion = Discussion.get_or_none(
        (Discussion.id == discussion_id) & (Discussion.repository == repo)
    )
    if not discussion:
        raise HTTPException(404, detail={"error": "Discussion not found"})

    comments = (
        DiscussionComment.select()
        .where(DiscussionComment.discussion == discussion)
        .order_by(DiscussionComment.created_at.asc())
    )

    return {
        "discussion": _discussion_payload(discussion),
        "comments": [_comment_payload(comment) for comment in comments],
    }


@router.post("/{repo_type}s/{namespace}/{name}/discussions/{discussion_id}/comments")
async def create_comment(
    repo_type: str,
    namespace: str,
    name: str,
    discussion_id: int,
    payload: CommentCreate,
    user: User = Depends(get_current_user),
):
    """Reply to a discussion thread."""
    repo = _get_visible_repo(repo_type, namespace, name, user)
    discussion = Discussion.get_or_none(
        (Discussion.id == discussion_id) & (Discussion.repository == repo)
    )
    if not discussion:
        raise HTTPException(404, detail={"error": "Discussion not found"})

    body = payload.body.strip()
    if not body:
        raise HTTPException(400, detail={"error": "Comment body is required"})

    with db.atomic():
        comment = DiscussionComment.create(
            discussion=discussion,
            author=user,
            body=body,
            created_at=_now(),
            updated_at=_now(),
        )
        discussion.updated_at = _now()
        discussion.save()

    return _comment_payload(comment)


@router.delete("/{repo_type}s/{namespace}/{name}/discussions/{discussion_id}")
async def delete_discussion(
    repo_type: str,
    namespace: str,
    name: str,
    discussion_id: int,
    user: User = Depends(get_current_user),
):
    """Delete a discussion thread."""
    repo = _get_visible_repo(repo_type, namespace, name, user)
    discussion = Discussion.get_or_none(
        (Discussion.id == discussion_id) & (Discussion.repository == repo)
    )
    if not discussion:
        raise HTTPException(404, detail={"error": "Discussion not found"})

    if not _can_manage_repo_item(repo, user, discussion.author_id):
        raise HTTPException(403, detail={"error": "No permission to delete discussion"})

    discussion.delete_instance(recursive=True)
    return {"success": True}


@router.delete(
    "/{repo_type}s/{namespace}/{name}/discussions/{discussion_id}/comments/{comment_id}"
)
async def delete_comment(
    repo_type: str,
    namespace: str,
    name: str,
    discussion_id: int,
    comment_id: int,
    user: User = Depends(get_current_user),
):
    """Delete a comment in a discussion thread."""
    repo = _get_visible_repo(repo_type, namespace, name, user)
    discussion = Discussion.get_or_none(
        (Discussion.id == discussion_id) & (Discussion.repository == repo)
    )
    if not discussion:
        raise HTTPException(404, detail={"error": "Discussion not found"})

    comment = DiscussionComment.get_or_none(
        (DiscussionComment.id == comment_id)
        & (DiscussionComment.discussion == discussion)
    )
    if not comment:
        raise HTTPException(404, detail={"error": "Comment not found"})

    if not _can_manage_repo_item(repo, user, comment.author_id):
        raise HTTPException(403, detail={"error": "No permission to delete comment"})

    comment.delete_instance()
    discussion.updated_at = _now()
    discussion.save()
    return {"success": True}
