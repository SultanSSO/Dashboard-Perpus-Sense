"""Backward-compatible entrypoint for selectable CCTV analysis modes."""

from vision_agent.cv.vision_cctv_modes import *  # noqa: F401,F403
from vision_agent.cv.vision_cctv_modes import main


if __name__ == "__main__":
    main()
