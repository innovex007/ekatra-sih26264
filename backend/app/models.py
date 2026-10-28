from datetime import date, datetime
from typing import Optional

from pydantic import NaiveDatetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Institution(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    permanent_id: str = Field(index=True)
    name: str
    aliases: list = Field(default_factory=list, sa_column=Column(JSON))
    acronym: str = ""
    state: str = ""
    district: str = ""
    city: str = ""
    pincode: str = ""
    region: str = ""
    type: str = ""


class Bureau(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: str  # case-id prefix


class Officer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    bureau_id: int
    role: str = "Officer"


class Case(SQLModel, table=True):
    id: str = Field(primary_key=True)
    bureau_id: int = Field(index=True)
    received_date: date
    source: str = ""
    category: str = ""
    description: str = ""
    institution_name_as_written: str = ""
    institution_id: Optional[int] = Field(default=None, index=True)
    suggested_institution_id: Optional[int] = None
    link_confidence: float = 0.0
    link_status: str = "unlinked"  # auto | confirmed | unlinked
    link_why: dict = Field(default_factory=dict, sa_column=Column(JSON))
    complainant_token: str = ""
    status: str = "Received"
    current_officer_id: Optional[int] = None
    last_action: str = ""
    next_action: str = ""
    sla_days: int = 21
    due_date: Optional[date] = None
    transfer_count: int = 0


class CaseAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    ts: NaiveDatetime
    actor: str = ""
    bureau: str = ""
    action: str = ""
    remarks: str = ""
    documents: list = Field(default_factory=list, sa_column=Column(JSON))
    finding_topic: Optional[str] = None      # lab | faculty | infrastructure | fees | safety
    finding_verdict: Optional[str] = None    # compliant | non-compliant | not verified
    prev_hash: str = ""
    hash: str = ""


class Cluster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    institution_id: int = Field(index=True)
    lead_bureau_id: Optional[int] = None
    status: str = "open"  # open | coordinated | closed
    joint_reply_text: str = ""
    severity: str = "RELATED"


class Overlap(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_a: str = Field(index=True)
    case_b: str = Field(index=True)
    severity: str
    reason: str = ""
    issue_similarity: float = 0.0
    created_at: NaiveDatetime
    resolved_by: Optional[str] = None
    cluster_id: Optional[int] = Field(default=None, index=True)


class Unlink(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_a: str
    case_b: str
    reason: str
    actor: str
    ts: NaiveDatetime


class InterlockEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    attempted_action: str
    blocking_case_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    outcome: str  # lead_assigned | override_with_reason | cancelled | warned
    reason: str = ""
    actor: str = ""
    ts: NaiveDatetime


class AuditEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: NaiveDatetime
    actor: str = ""
    role: str = ""
    action: str = ""
    entity: str = ""
    payload_json: str = "{}"
    prev_hash: str = ""
    hash: str = ""


class Meta(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str = ""
