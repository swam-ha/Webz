from abc import ABC, abstractmethod
from typing import List, Any, TypedDict

class ScanResult(TypedDict):
    name: str
    target: str|None
    result: Any

class BaseScanner(ABC):

    def return_value(self, result, target)-> ScanResult:
        return {
            "name": self.name,
            "target": target,
            "result": result
        }

    @property
    @abstractmethod
    def name(self) -> str:
        # Any scanner MUST define a name.
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod # return name, target result
    def run(self, args: List) -> ScanResult:
        # entry point
        # any scanner MUST define a run method.
        pass
