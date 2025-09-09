"""Auto-generated protobuf stubs for easy import.
Generated on Mon 08 Sep 2025 03:03:08 AM +07
"""

# Import all protobuf modules (package-relative)
from .embedder_pb2 import *
from .rag_pb2 import *
from .embedder_pb2_grpc import *
from .rag_pb2_grpc import *

# Expose absolute names expected by grpc stubs (e.g. 'embedder_pb2')
import sys as _sys
from importlib import import_module as _im
_sys.modules.setdefault('embedder_pb2', _im('.embedder_pb2', package=__name__))
_sys.modules.setdefault('rag_pb2', _im('.rag_pb2', package=__name__))

__all__ = [name for name in dir() if not name.startswith('_')]
