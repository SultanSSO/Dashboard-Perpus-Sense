"""Backward-compatible entrypoint for the person counter."""

from vision_agent.cv.person_counter import *  # noqa: F401,F403
from vision_agent.cv.person_counter import main


if __name__ == "__main__":
    main()
