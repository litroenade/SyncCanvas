"""
Agent Lib 模块
"""


def __getattr__(name: str):
    """延迟导入所有子模块和组件"""
    if name == "canvas":
        from src.agent.lib import canvas
        return canvas
    elif name == "library":
        from src.agent.lib import library
        return library
    elif name == "tools":
        from src.agent.lib import tools
        return tools
    elif name == "version_control":
        from src.agent.lib import version_control
        return version_control
    elif name == "utils":
        from src.agent.lib import utils
        return utils
    elif name == "LibraryService":
        from src.agent.lib.library import LibraryService
        return LibraryService
    elif name == "library_service":
        from src.agent.lib.library import library_service
        return library_service
    elif name == "Library":
        from src.agent.lib.library import Library
        return Library
    elif name == "LibraryItem":
        from src.agent.lib.library import LibraryItem
        return LibraryItem
    elif name == "IGitService":
        from src.agent.lib.version_control import IGitService
        return IGitService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__: list[str] = []
