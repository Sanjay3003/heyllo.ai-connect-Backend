"""Enum definitions for database models"""

import enum


class LeadStatus(str, enum.Enum):
    """Lead status enum"""
    NEW = "new"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CALLBACK = "callback"
    DO_NOT_CALL = "do_not_call"


class CallStatus(str, enum.Enum):
    """Call status enum"""
    PENDING = "pending"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class CallOutcome(str, enum.Enum):
    """Call outcome enum"""
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CALLBACK = "callback"
    NO_ANSWER = "no_answer"
    VOICEMAIL = "voicemail"


class CampaignStatus(str, enum.Enum):
    """Campaign status enum"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
