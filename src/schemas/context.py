from typing import Literal, Optional, List
from pydantic import BaseModel, Field

AiConversationPhase = Literal[
    "intro",
    "personal",
    "experience",
    "education",
    "projects",
    "review",
]


class AiChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class AiRequestContext(BaseModel):
    """
    Context sent by frontend / caller for CV tailoring and assistance.
    """
    prompt: str = Field(..., description="User prompt or instruction")
    cvYaml: Optional[str] = Field(default=None, description="Current CV in YAML format")
    jd: Optional[str] = Field(default=None, description="Target job description")
    language: Optional[str] = Field(default="en", description="Language code (e.g. 'vi', 'en')")
    history: Optional[List[AiChatMessage]] = Field(default=None, description="Conversation history")
    phase: Optional[AiConversationPhase] = Field(default=None, description="Current conversation phase")
