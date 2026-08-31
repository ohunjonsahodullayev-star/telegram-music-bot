"""
Handlerlar to'plami.
"""

from .music import music_router
from .start import start_router

__all__ = ["start_router", "music_router"]
