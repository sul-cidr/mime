import json
from decimal import Decimal
from uuid import UUID

import asyncpg
import numpy as np
from asyncpg.pgproto import pgproto  # type: ignore


class MimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        type_map = {
            asyncpg.Record: lambda obj: dict(obj.items()),
            Decimal: float,
            np.floating: float,
            np.integer: int,
            np.ndarray: lambda arr: arr.tolist(),
            pgproto.UUID: str,
            UUID: str,
        }
        conversion_func = type_map.get(type(obj), super().default)
        return conversion_func(obj)
