"""Backward-compatible import path for the latest-frame worker."""

from vision_agent.cv.video_worker import FrameResult, LatestFrameWorker

__all__ = ["LatestFrameWorker", "FrameResult"]
