from __future__ import annotations

from typing import Iterable, Mapping, Sequence, Tuple

import numpy as np


class VectorProcessor:
    def to_f32_list(self, values: np.ndarray | Iterable[float]) -> list[float]:
        if isinstance(values, np.ndarray):
            return [float(item) for item in values.astype(np.float32, copy=False).tolist()]
        return [float(np.float32(item)) for item in values]


    def l2_normalize(
        self,
        vector: list[float]
    ) -> list[float]:
        arr = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(arr))

        if norm == 0.0:
            return self.to_f32_list(arr)

        return self.to_f32_list(arr / norm)


    def extract_dense_vector(
        self,
        encode_result: Mapping[str, object],
        idx: int,
    ) -> list[float]:
        dense_vecs = encode_result.get("dense_vecs")
        if dense_vecs is None:
            return []
        arr = np.asarray(dense_vecs, dtype=np.float32)
        if arr.ndim == 1:
            vec = arr
        else:
            if idx < 0 or idx >= arr.shape[0]:
                return []
            vec = arr[idx]
        return self.to_f32_list(vec)


    def extract_sparse_vector(
        self,
        encode_result: Mapping[str, object],
        idx: int,
    ) -> Tuple[list[int], list[float]] | None:
        sparse_vecs = encode_result.get("lexical_weights")
        if not isinstance(sparse_vecs, Sequence):
            return None

        sparse_value = sparse_vecs[idx]

        if isinstance(sparse_value, dict):
            if not sparse_value:
                return None
            items = sorted((int(k), float(v)) for k, v in sparse_value.items())
            indices = [i for i, _ in items]
            values = [v for _, v in items]
            return indices, self.to_f32_list(values)

        if hasattr(sparse_value, "indices") and hasattr(sparse_value, "data"):
            indices = sparse_value.indices.astype(np.uint32, copy=False).tolist()
            values = self.to_f32_list(sparse_value.data)
            if not indices:
                return None
            return indices, values

        return None
