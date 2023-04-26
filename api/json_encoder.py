import json

import asyncpg
import numpy as np


class MimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        type_map = {
            np.integer: int,
            np.floating: float,
            np.ndarray: lambda arr: arr.tolist(),
            asyncpg.Record: lambda obj: dict(obj.items()),
        }
        conversion_func = type_map.get(type(obj), super().default)
        return conversion_func(obj)
