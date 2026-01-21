import json
import os
from functools import wraps
from aiocache import Cache
from aiocache.serializers import PickleSerializer

cache = Cache(
    Cache.REDIS,
    endpoint=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    namespace="activity_info",
    ttl=3600,
    serializer=PickleSerializer()
)

def auto_cache(ttl=3600, model=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            bypass_cache = kwargs.pop("_bypass_cache", False)
            if not bypass_cache:
                key_args = [str(a) for a in args[1:]]  # skip self
                key_kwargs = {k: str(v) for k, v in kwargs.items()}
                cache_key = (
                    f"{func.__name__}:"
                    f"{json.dumps(key_args)}:"
                    f"{json.dumps(key_kwargs, sort_keys=True)}"
                )
                result = await cache.get(cache_key)
                if result is not None:
                    if model:
                        if isinstance(result, list):
                            return [model.model_validate(x) for x in result]
                        return model.model_validate(result)
                    return result
            result = await func(*args, **kwargs)
            if not bypass_cache:
                if isinstance(result, list):
                    result_to_cache = [
                        x.model_dump() if hasattr(x, "model_dump") else x
                        for x in result
                    ]
                elif hasattr(result, "model_dump"):
                    result_to_cache = result.model_dump()
                else:
                    result_to_cache = result
                await cache.set(cache_key, result_to_cache, ttl=ttl)
            return result
        return wrapper
    return decorator

