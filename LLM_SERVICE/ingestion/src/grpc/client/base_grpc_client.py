from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic

import grpc
from loguru import logger
from protovalidate import Validator, ValidationError

from protobuf_stubs import embedder_pb2


T = TypeVar('T')


class BaseGrpcClient(ABC, Generic[T]):
    def __init__(self, channel: grpc.Channel) -> None:
        self.channel = channel
        self.validator = Validator()


    def _validate_request(self, request: T) -> None:
        try:
            self.validator.validate(request)
            
        except ValidationError as e:
            logger.error(f"Request validation failed: {e}")
            raise ValueError(f"Invalid request: {e}")


    def _validate_response(self, response: Any) -> None:
        try:
            self.validator.validate(response)

        except ValidationError as e:
            logger.error(f"Response validation failed: {e}")
            raise ValueError(f"Invalid response: {e}")

