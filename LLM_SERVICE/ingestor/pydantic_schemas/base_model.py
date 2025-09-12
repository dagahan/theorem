from typing import Annotated
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    text,
)

from enum import Enum as PyEnum

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


UUIDpk = Annotated[UUID,
        mapped_column(UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )]
    
created_at = Annotated[int, mapped_column(
    BigInteger,
    server_default=text("(EXTRACT(EPOCH FROM NOW()))::bigint"),
    nullable=False)
]

updated_at = Annotated[int, mapped_column(
    BigInteger,
    server_default=text("(EXTRACT(EPOCH FROM NOW()))::bigint"),
    onupdate=text("(EXTRACT(EPOCH FROM NOW()))::bigint"),
    nullable=False)
]


class Base(DeclarativeBase):
    # this is base class for all of declaratively using models of tables.
    # e.g. we use this for create or drop all of tables in db.
    pass


    