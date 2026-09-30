"""Backward-compatible import path for the CCTV MCP domain service."""

from vision_agent.mcp.service import CCTVPaths, CCTVService, CCTVServiceError

__all__ = ["CCTVPaths", "CCTVService", "CCTVServiceError"]
