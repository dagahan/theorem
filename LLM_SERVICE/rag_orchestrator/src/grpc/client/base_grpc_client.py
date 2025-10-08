from abc import ABC
from typing import Any, TypeVar, Generic

import grpc
from loguru import logger
from protovalidate import Validator, ValidationError



T = TypeVar('T')


class BaseGrpcClient(ABC, Generic[T]):
    def __init__(self, channel: grpc.Channel) -> None:
        self.channel = channel
        self.validator = Validator()


    def _validate_request(
        self,
        request: T
    ) -> None:
        try:
            self.validator.validate(request)
            
        except ValidationError as ex:
            logger.error(f"Request validation failed: {ex}")
            raise ValueError(f"Invalid request: {ex}")


    def _validate_response(
        self,
        response: Any
    ) -> None:
        try:
            self.validator.validate(response)

        except ValidationError as ex:
            logger.error(f"Response validation failed: {ex}")
            raise ValueError(f"Invalid response: {ex}")

