"""Schemas Pydantic dos payloads do WhatsApp Cloud API.

Estrutura simplificada conforme documentação Meta. Apenas os campos que
consumimos são modelados; o restante é ignorado via `extra="ignore"`.
Referência: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components
"""

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppTextBody(BaseModel):
    body: str

    model_config = ConfigDict(extra="ignore")


class WhatsAppIncomingMessage(BaseModel):
    id: str
    from_phone: str = Field(alias="from")
    timestamp: str
    type: str
    text: WhatsAppTextBody | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class WhatsAppContactProfile(BaseModel):
    name: str | None = None

    model_config = ConfigDict(extra="ignore")


class WhatsAppContact(BaseModel):
    wa_id: str
    profile: WhatsAppContactProfile | None = None

    model_config = ConfigDict(extra="ignore")


class WhatsAppValue(BaseModel):
    messaging_product: str
    contacts: list[WhatsAppContact] | None = None
    messages: list[WhatsAppIncomingMessage] | None = None

    model_config = ConfigDict(extra="ignore")


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str

    model_config = ConfigDict(extra="ignore")


class WhatsAppEntry(BaseModel):
    id: str
    changes: list[WhatsAppChange]

    model_config = ConfigDict(extra="ignore")


class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: list[WhatsAppEntry]

    model_config = ConfigDict(extra="ignore")
