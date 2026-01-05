import uuid
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Base(DeclarativeBase):
    pass

def _uuid():
    return uuid.uuid4()

class CaseFile(Base):
    __tablename__ = "case_files"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    status: Mapped[str] = mapped_column(Text, default="intake")  # intake/needs_info/ready/running/completed/failed
    client_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    complexity_level: Mapped[int] = mapped_column(Integer, default=1)
    workflow_key: Mapped[str] = mapped_column(Text, default="WF_SIMPLE_QUOTE")

    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # 0..1
    missing_fields = mapped_column(JSONB, nullable=True)
    assumptions = mapped_column(JSONB, nullable=True)
    normalized_request = mapped_column(JSONB, nullable=True)
    tags = mapped_column(JSONB, nullable=True)

class CaseInput(Base):
    __tablename__ = "case_inputs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    source_type: Mapped[str] = mapped_column(Text)  # email_text/attachment/manual_form/excel/pdf/image
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_json = mapped_column(JSONB, nullable=True)

class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    event_type: Mapped[str] = mapped_column(Text)
    payload = mapped_column(JSONB, nullable=True)

class CaseTask(Base):
    __tablename__ = "case_tasks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    step_key: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="queued")  # queued/running/done/failed/skipped
    input_json = mapped_column(JSONB, nullable=True)
    output_json = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class CaseOutput(Base):
    __tablename__ = "case_outputs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    case_id = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    output_type: Mapped[str] = mapped_column(Text)  # quote_json/report_json/scenarios_json/...
    content_json = mapped_column(JSONB, nullable=True)
    file_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
