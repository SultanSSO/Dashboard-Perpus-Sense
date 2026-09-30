"""MCP server for the Vision Agent CCTV project.

Run locally with:
    .\\venv\\Scripts\\mcp.exe dev mcp_cctv_server.py

Run as Streamable HTTP:
    .\\venv\\Scripts\\mcp.exe run mcp_cctv_server.py --transport streamable-http

The server exposes narrow, typed tools. It never returns camera credentials,
raw URL templates, or arbitrary shell/database access.
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from mcp.server import MCPServer

from vision_agent.mcp.service import CCTVService, CCTVServiceError


mcp = MCPServer("cctv-vision")
SERVICE = CCTVService.from_env()


def _actor() -> str:
    return os.getenv("MCP_ACTOR_ID", "mcp-local")


def _mutations_enabled() -> bool:
    return os.getenv("MCP_ENABLE_MUTATIONS", "false").casefold() == "true"


def _envelope(
    *,
    action: str,
    data: Any = None,
    error: dict[str, Any] | None = None,
    request_id: str | None = None,
    audit_id: str | None = None,
) -> dict[str, Any]:
    request_id = request_id or f"REQ-{uuid.uuid4().hex[:12]}"
    if audit_id is None:
        try:
            audit_id = SERVICE.audit(action, _actor(), {"ok": error is None})
        except OSError:
            audit_id = None
    return {
        "ok": error is None,
        "request_id": request_id,
        "data": data,
        "error": error,
        "audit_id": audit_id,
    }


def _run(action: str, operation, request_id: str | None = None) -> dict[str, Any]:
    try:
        return _envelope(action=action, data=operation(), request_id=request_id)
    except CCTVServiceError as exc:
        return _envelope(
            action=action,
            error={"code": exc.code, "reason": exc.message},
            request_id=request_id,
        )
    except Exception as exc:  # Never expose a stack trace or secret to an MCP client.
        return _envelope(
            action=action,
            error={"code": "INTERNAL_ERROR", "reason": f"{type(exc).__name__}: operasi gagal"},
            request_id=request_id,
        )


def _require_mutations() -> None:
    if not _mutations_enabled():
        raise CCTVServiceError(
            "ACTION_DENIED",
            "Mutasi dinonaktifkan. Set MCP_ENABLE_MUTATIONS=true setelah gateway authorization siap.",
        )


@mcp.tool(name="service.health")
def service_health(request_id: str | None = None) -> dict[str, Any]:
    """Check catalog, event store, task registry, and worker connectivity."""
    return _run("service.health", SERVICE.health, request_id)


@mcp.tool(name="agent.settings.get")
def agent_settings_get(request_id: str | None = None) -> dict[str, Any]:
    """Get persisted agent defaults, including whether every supported task must run."""
    return _run("agent.settings.get", SERVICE.agent_settings, request_id)


@mcp.tool(name="agent.settings.configure")
def agent_settings_configure(
    run_all_tasks: bool,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Enable or disable the audited default that keeps all supported tasks running."""
    try:
        _require_mutations()
        settings, audit_id = SERVICE.configure_agent_settings(
            run_all_tasks=run_all_tasks,
            actor_id=_actor(),
        )
        return _envelope(
            action="agent.settings.configure",
            data=settings,
            request_id=request_id,
            audit_id=audit_id,
        )
    except CCTVServiceError as exc:
        return _envelope(
            action="agent.settings.configure",
            error={"code": exc.code, "reason": exc.message},
            request_id=request_id,
        )


@mcp.tool(name="camera.list")
def camera_list(
    status: str | None = None,
    location: str | None = None,
    analysis_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    request_id: str | None = None,
) -> dict[str, Any]:
    """List sanitized CCTV metadata with bounded pagination."""
    return _run(
        "camera.list",
        lambda: SERVICE.list_cameras(
            status=status,
            location=location,
            analysis_only=analysis_only,
            limit=limit,
            offset=offset,
        ),
        request_id,
    )


@mcp.tool(name="camera.get_metadata")
def camera_get_metadata(camera_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Get sanitized metadata for one camera; credentials and URL templates are excluded."""
    return _run("camera.get_metadata", lambda: SERVICE.get_metadata(camera_id), request_id)


@mcp.tool(name="camera.get_status")
def camera_get_status(camera_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Get catalog health and the latest camera-scoped event state."""
    return _run("camera.get_status", lambda: SERVICE.get_status(camera_id), request_id)


@mcp.tool(name="vision.get_current_observation")
def vision_get_current_observation(camera_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Get the latest camera-scoped structured observation, without raw frames."""
    return _run("vision.get_current_observation", lambda: SERVICE.current_observation(camera_id), request_id)


@mcp.tool(name="analytics.events")
def analytics_events(
    camera_id: str | None = None,
    event_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int = 50,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Query bounded, redacted vision events."""
    return _run(
        "analytics.events",
        lambda: SERVICE.events(
            camera_id=camera_id,
            event_type=event_type,
            start=start,
            end=end,
            limit=limit,
        ),
        request_id,
    )


@mcp.tool(name="analytics.summary")
def analytics_summary(
    camera_ids: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return deterministic people-count aggregates from structured events."""
    return _run(
        "analytics.summary",
        lambda: SERVICE.summary(camera_ids=camera_ids, start=start, end=end),
        request_id,
    )


@mcp.tool(name="task.list")
def task_list(
    status: str | None = None,
    limit: int = 50,
    request_id: str | None = None,
) -> dict[str, Any]:
    """List persisted local task records."""
    return _run("task.list", lambda: SERVICE.list_tasks(status=status, limit=limit), request_id)


@mcp.tool(name="task.get")
def task_get(task_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Get one authoritative task record from the local registry."""
    return _run("task.get", lambda: SERVICE.get_task(task_id), request_id)


@mcp.tool(name="task.configure")
def task_configure(
    task_id: str,
    rule: dict[str, Any],
    enabled: bool,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Replace a supported task rule and set its RUNNING or PAUSED state."""
    try:
        _require_mutations()
        task, audit_id = SERVICE.configure_task(
            task_id=task_id,
            rule=rule,
            enabled=enabled,
            actor_id=_actor(),
        )
        return _envelope(
            action="task.configure",
            data=task,
            request_id=request_id,
            audit_id=audit_id,
        )
    except CCTVServiceError as exc:
        return _envelope(
            action="task.configure",
            error={"code": exc.code, "reason": exc.message},
            request_id=request_id,
        )


@mcp.tool(name="task.create")
def task_create(
    name: str,
    goal: str,
    camera_ids: list[str],
    task_type: str = "MONITOR",
    rule: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create a validated task; execution requires a separately configured scheduler."""
    try:
        _require_mutations()
        task, audit_id = SERVICE.create_task(
            name=name,
            goal=goal,
            camera_ids=camera_ids,
            task_type=task_type,
            actor_id=_actor(),
            rule=rule,
        )
        return _envelope(action="task.create", data=task, request_id=request_id, audit_id=audit_id)
    except CCTVServiceError as exc:
        return _envelope(action="task.create", error={"code": exc.code, "reason": exc.message}, request_id=request_id)


@mcp.tool(name="task.transition")
def task_transition(
    task_id: str,
    target_status: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Pause, resume, or cancel a task after mutation authorization is enabled."""
    try:
        _require_mutations()
        task, audit_id = SERVICE.transition_task(
            task_id=task_id,
            target_status=target_status,
            actor_id=_actor(),
        )
        return _envelope(action="task.transition", data=task, request_id=request_id, audit_id=audit_id)
    except CCTVServiceError as exc:
        return _envelope(action="task.transition", error={"code": exc.code, "reason": exc.message}, request_id=request_id)


@mcp.resource("cctv://health")
def health_resource() -> str:
    """Machine-readable service health resource for MCP hosts."""
    return json.dumps(SERVICE.health(), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # The official MCP CLI is preferred because it selects the transport.
    # This fallback supports direct local execution when the SDK exposes run().
    mcp.run()
