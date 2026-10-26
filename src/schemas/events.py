from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from .context import AiConversationPhase


class YamlPatch(BaseModel):
    tab: Literal["cv"] = "cv"
    yaml: str


class GapItem(BaseModel):
    field: str
    message: str
    severity: Literal["required", "recommended"]


class AiQuestionEvent(BaseModel):
    type: Literal["question"] = "question"
    phase: AiConversationPhase
    question: str
    field: Optional[str] = None
    optional: bool = False


class AiPartialUpdateEvent(BaseModel):
    type: Literal["partial_update"] = "partial_update"
    phase: AiConversationPhase
    message: str
    yamlPatch: YamlPatch


class AiGapReportEvent(BaseModel):
    type: Literal["gap_report"] = "gap_report"
    gaps: List[GapItem] = Field(default_factory=list)
    question: str


class AiDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    message: str
    cvYaml: str


class AiProgressEvent(BaseModel):
    step: str
    message: str


AiResponseEvent = Annotated[
    Union[
        AiQuestionEvent,
        AiPartialUpdateEvent,
        AiGapReportEvent,
        AiDoneEvent,
    ],
    Field(discriminator="type"),
]
