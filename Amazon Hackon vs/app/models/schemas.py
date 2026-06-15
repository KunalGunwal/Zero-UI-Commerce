from pydantic import BaseModel, Field
from typing import List, Optional

# 1. Contact & Profile Info
class Profile(BaseModel):
    name: str

class Contact(BaseModel):
    profile: Profile
    wa_id: str

# 2. Message Types
class TextContent(BaseModel):
    body: str

class AudioContent(BaseModel):
    id: str

class Message(BaseModel):
    # 'from' is a reserved Python keyword, so we use Pydantic's alias feature
    from_field: str = Field(alias="from")
    id: str
    type: str
    text: Optional[TextContent] = None
    audio: Optional[AudioContent] = None

# 3. The Core Payload Structure
class Value(BaseModel):
    messaging_product: str
    contacts: Optional[List[Contact]] = None
    messages: Optional[List[Message]] = None

class Change(BaseModel):
    value: Value
    field: str

class Entry(BaseModel):
    id: str
    changes: List[Change]

class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[Entry]