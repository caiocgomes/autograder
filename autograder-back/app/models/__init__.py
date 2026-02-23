# Database models
from .base import Base
from .user import User, UserRole, LifecycleStatus
from .class_models import Class, ClassEnrollment, Group, GroupMembership, EnrollmentSource
from .exercise import (
    Exercise,
    TestCase,
    ExerciseList,
    ExerciseListItem,
    ProgrammingLanguage,
    SubmissionType,
    GradingMode,
    RubricDimension,
)
from .submission import (
    Submission,
    TestResult,
    LLMEvaluation,
    Grade,
    SubmissionStatus,
    RubricScore,
)
from .product import Product, ProductAccessRule, AccessRuleType
from .event import Event, EventStatus
from .student_course_status import StudentCourseStatus
from .hotmart_buyer import HotmartBuyer
from .hotmart_product_mapping import HotmartProductMapping
from .message_campaign import MessageCampaign, MessageRecipient, CampaignStatus, RecipientStatus
from .message_template import MessageTemplate, TemplateEventType

__all__ = [
    "Base",
    "User",
    "UserRole",
    "LifecycleStatus",
    "Class",
    "ClassEnrollment",
    "Group",
    "GroupMembership",
    "EnrollmentSource",
    "Exercise",
    "TestCase",
    "ExerciseList",
    "ExerciseListItem",
    "ProgrammingLanguage",
    "SubmissionType",
    "GradingMode",
    "RubricDimension",
    "Submission",
    "TestResult",
    "LLMEvaluation",
    "Grade",
    "SubmissionStatus",
    "RubricScore",
    "Product",
    "ProductAccessRule",
    "AccessRuleType",
    "Event",
    "EventStatus",
    "StudentCourseStatus",
    "HotmartBuyer",
    "HotmartProductMapping",
    "MessageCampaign",
    "MessageRecipient",
    "CampaignStatus",
    "RecipientStatus",
    "MessageTemplate",
    "TemplateEventType",
]
