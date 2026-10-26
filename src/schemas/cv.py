from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, Field

EntryType = Literal[
    "Text",
    "Experience",
    "Education",
    "Publication",
    "One-Line",
    "Bullet",
    "Numbered",
    "Reversed Numbered",
    "Normal",
]


class BaseEntry(BaseModel):
    id: str


class TextEntry(BaseEntry):
    type: Literal["Text"] = "Text"
    text: str


class ExperienceEntry(BaseEntry):
    type: Literal["Experience"] = "Experience"
    company: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class EducationEntry(BaseEntry):
    type: Literal["Education"] = "Education"
    institution: str
    area: str
    degree: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class NormalEntry(BaseEntry):
    type: Literal["Normal"] = "Normal"
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class PublicationEntry(BaseEntry):
    type: Literal["Publication"] = "Publication"
    title: str
    authors: List[str] = Field(default_factory=list)
    journal: str
    date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class OneLineEntry(BaseEntry):
    type: Literal["One-Line"] = "One-Line"
    label: str
    details: str


class BulletEntry(BaseEntry):
    type: Literal["Bullet"] = "Bullet"
    bullet: str


class NumberedEntry(BaseEntry):
    type: Literal["Numbered"] = "Numbered"
    text: str
    number: Optional[int] = None


class ReversedNumberedEntry(BaseEntry):
    type: Literal["Reversed Numbered"] = "Reversed Numbered"
    text: str
    number: Optional[int] = None


CvEntry = Annotated[
    Union[
        TextEntry,
        ExperienceEntry,
        EducationEntry,
        NormalEntry,
        PublicationEntry,
        OneLineEntry,
        BulletEntry,
        NumberedEntry,
        ReversedNumberedEntry,
    ],
    Field(discriminator="type"),
]


class SocialNetwork(BaseModel):
    id: str
    network: str
    username: str


class CvSection(BaseModel):
    id: str
    title: str
    entryType: EntryType
    entries: List[CvEntry] = Field(default_factory=list)


class CvAiData(BaseModel):
    name: str
    headline: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    photo_url: Optional[str] = None
    social_networks: Optional[List[SocialNetwork]] = None
    sections: List[CvSection] = Field(default_factory=list)
