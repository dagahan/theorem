from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..base_model import *


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True, primary_key=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(63), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    collection_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    def __repr__(self) -> str:
        return f"<Document(doc_id='{self.doc_id}', collection='{self.collection_name}')>"


        