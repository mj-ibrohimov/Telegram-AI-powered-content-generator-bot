from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    source_url: str
    publication_date: str


class NewsProvider(ABC):
    @abstractmethod
    async def search(self, query: str) -> list[NewsItem]:
        ...
