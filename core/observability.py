from collections.abc import Callable
from typing import Any


try:
    from langsmith import traceable as _langsmith_traceable
except ImportError:  # pragma: no cover
    _langsmith_traceable = None


def traceable(*args: Any, **kwargs: Any) -> Callable:
    """LangSmith traceable 装饰器包装，缺失依赖时自动降级为 no-op。"""
    if _langsmith_traceable is None:
        def decorator(func: Callable) -> Callable:
            return func

        return decorator
    return _langsmith_traceable(*args, **kwargs)
