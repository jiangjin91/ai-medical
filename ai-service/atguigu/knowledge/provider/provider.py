from abc import ABC, abstractmethod

from pydantic.dataclasses import dataclass

from atguigu.domain.state import DialogueState


@dataclass(slots=True)
class KnowledgeChunk:
    content: str

class Provider(ABC):
    provider_id: str

    @abstractmethod
    async def retrival(self, dialogue_state: DialogueState) -> list[KnowledgeChunk]:
        pass