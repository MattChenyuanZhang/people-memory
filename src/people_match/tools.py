"""Model-independent tool contracts, shared by CLI and MCP."""
from .core import Memory


def get_preferences():
    """Read recording preferences before automatic writes."""
    with_memory = Memory()
    try:
        return with_memory.preferences()
    finally:
        with_memory.close()


def call(method, **kwargs):
    memory=Memory()
    try:
        return getattr(memory,method)(**kwargs)
    finally:
        memory.close()
