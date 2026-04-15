"""
Enums de domínio — valores válidos para campos restritos nos models.

Usar enum no model + CHECK constraint no banco garante integridade
na fonte, independente de validação na aplicação.
"""

from enum import Enum


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class MessageSender(str, Enum):
    USER = "user"
    BOT = "bot"


class DocumentCategory(str, Enum):
    SERVICES = "services"
    HOURS = "hours"
    POLICIES = "policies"
    FAQ = "faq"
    GENERAL = "general"


class UserRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
