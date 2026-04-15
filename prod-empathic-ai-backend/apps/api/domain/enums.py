from enum import Enum


class ConceptLabel(str, Enum):
    PERSON = "Person"
    TRIGGER = "Trigger"
    EMOTION = "Emotion"
    BELIEF = "Belief"
    NEED = "Need"
    GOAL = "Goal"
    ACTION = "Action"
    EVENT = "Event"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


class GraphRelationshipType(str, Enum):
    HAS_UTTERANCE = "HAS_UTTERANCE"
    MENTIONS = "MENTIONS"
    EVOKES = "EVOKES"
    DRIVES = "DRIVES"
    LEADS_TO = "LEADS_TO"
    AFFECTS = "AFFECTS"
    SUPPORTS = "SUPPORTS"
    CONFLICTS_WITH = "CONFLICTS_WITH"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]
