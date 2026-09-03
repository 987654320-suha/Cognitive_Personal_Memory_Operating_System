"""
CogniSphere Desktop Agent package.
"""
from desktop_agent.config import AgentConfig
from desktop_agent.scanner import FolderScanner, LocalManifest
from desktop_agent.watcher import WatcherManager
from desktop_agent.sync_queue import SyncQueue
from desktop_agent.client import BackendClient
from desktop_agent.parsers import ParserRegistry

__all__ = [
    "AgentConfig",
    "FolderScanner",
    "LocalManifest",
    "WatcherManager",
    "SyncQueue",
    "BackendClient",
    "ParserRegistry",
]
