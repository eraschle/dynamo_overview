from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List


@dataclass
class CodeNode:
    uuid: str
    name: str
    code: str
    engine: str


@dataclass
class DynamoFile:
    uuid: str = field(compare=True, repr=True)
    name: str = field(compare=False, repr=True)
    root_path: Path = field(compare=False, repr=False)
    path: Path = field(compare=True, repr=True)
    dependencies: List[str] = field(compare=False, repr=False)
    nodes: List[CodeNode] = field(compare=False, repr=False)

    @property
    def key(self) -> str:
        return f"{self.uuid}-{self.sub_path}"

    @property
    def sub_path(self) -> str:
        root = str(self.root_path)
        file = str(self.path)
        return file.replace(root, "")

    @property
    def is_unused(self) -> bool:
        return len(self.node_used_in()) == 0

    @property
    def has_dependency(self) -> bool:
        return len(self.dependencies) > 0

    @property
    def is_custom_node(self) -> bool:
        return self.path.suffix.lower().endswith("dyf")

    @property
    def is_script(self) -> bool:
        return self.path.suffix.lower().endswith("dyn")

    @abstractmethod
    def add_used_in(self, nodes: Iterable["DynamoFile"]) -> None:
        pass

    @abstractmethod
    def node_used_in(self) -> List["DynamoFile"]:
        pass


@dataclass
class CustomNodeFile(DynamoFile):
    categories: List[str] = field(compare=False, repr=False)
    used_in: List[DynamoFile] = field(default_factory=list, compare=False, repr=False)

    def add_used_in(self, nodes: Iterable[DynamoFile]) -> None:
        nodes = [node for node in nodes if self.uuid in node.dependencies]
        nodes = [node for node in nodes if node not in self.used_in]
        if len(nodes) > 0:
            self.used_in.extend(nodes)

    @property
    def is_generated(self) -> bool:
        return self.path.name.startswith("Generate")

    def node_used_in(self) -> List[DynamoFile]:
        return sorted(self.used_in, key=lambda ele: ele.name)


@dataclass
class ScriptFile(DynamoFile):
    def add_used_in(self, _: Iterable[DynamoFile]) -> None:
        pass

    def node_used_in(self) -> List[DynamoFile]:
        return []
