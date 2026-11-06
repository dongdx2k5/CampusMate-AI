import enum

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    LECTURER = "LECTURER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"

class UnitKind(str, enum.Enum):
    FACULTY = "FACULTY"
    DEPARTMENT = "DEPARTMENT"
    CENTER = "CENTER"

class DocumentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"

class VersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"

class MessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"

class IntentEnum(str, enum.Enum):
    REGULATION = "REGULATION"
    SCHEDULE = "SCHEDULE"
    ROOM = "ROOM"
    SERVICE = "SERVICE"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"

class FeedbackRating(str, enum.Enum):
    HELPFUL = "HELPFUL"
    UNHELPFUL = "UNHELPFUL"

class AnnouncementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    REVOKED = "REVOKED"

class RoomType(str, enum.Enum):
    CLASSROOM = "CLASSROOM"
    LAB = "LAB"
    SELF_STUDY = "SELF_STUDY"
    COMMON_SPACE = "COMMON_SPACE"

class ScheduleEntryType(str, enum.Enum):
    CLASS = "CLASS"
    EXAM = "EXAM"
    BOOKING = "BOOKING"

