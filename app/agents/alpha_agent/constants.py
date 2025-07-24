from enum import Enum


class TaskStatus(Enum):
    """Task status enumeration"""
    APPROVED = "Approved"
    DONE = "Done"
    IN_PROGRESS = "In Progress"
    PENDING = "Pending"
    BLOCKED = "Blocked"


class IntentType(Enum):
    """User intent types"""
    QUERY_STATUS = "query_status"
    UPDATE_TASK = "update_task"
    GENERAL_QUESTION = "general_question"
    DEADLINE_INQUIRY = "deadline_inquiry"
    TEAM_INTERACTION = "team_interaction"


class ResponseType(Enum):
    """Response types"""
    INFORMATIONAL = "informational"
    ACTIONABLE = "actionable"
    CONVERSATIONAL = "conversational"


class MondayColumnIds:
    """Monday.com column IDs"""
    PERSON = "person"
    DATE = "date4"
    STATUS = "status"
    CLIENT = "dropdown_mksnbmk2"
    MIRO_LINK = "link_mksnj6fc"
    DRIVE_LINK = "link_mksn5w3"
    FRAMEIO_LINK = "link_mksnvt1d"
    NOTES = "long_text_mksn8vr6"
    PRIORITY = "text_mksnh90q"
