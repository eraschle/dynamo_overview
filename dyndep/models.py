from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple, Type, TypeVar


class DynFile(Protocol):
    file_id: str
    name: str
    type: str

    def getvalue(self) -> bytes: ...


@dataclass
class BaseNode:
    uuid: str
    name: str
    content: Dict[str, Any]
    group: Optional["Annotation"]

    @property
    def has_group(self) -> bool:
        return self.group is not None


@dataclass
class Annotation(BaseNode):
    nodes: List[BaseNode]

    def __post_init__(self):
        for node in self.nodes:
            node.group = self


@dataclass
class DynamoNode(BaseNode):
    node_type: str
    concrete_type: str


@dataclass
class PythonCodeNode(DynamoNode):
    code: str
    engine: str


@dataclass
class Package:
    @classmethod
    def default(cls) -> "Package":
        return Package(name="DEFAULT", version="0.0.0")

    name: str
    version: str


@dataclass
class CustomNode(DynamoNode):
    custom_uuid: str
    package: Package


TNode = TypeVar("TNode", bound=DynamoNode)


@dataclass
class DynamoFile:
    uuid: str = field(compare=True, repr=True)
    name: str = field(compare=False, repr=True)
    file: DynFile = field(compare=False, repr=False)
    dependencies: List[str] = field(compare=False, repr=False)
    nodes: List[DynamoNode] = field(compare=False, repr=False)
    groups: List[Annotation] = field(compare=False, repr=False)

    @property
    def has_groups(self) -> bool:
        return len(self.groups) > 0

    def has_nodes(self, node_type: Type[TNode]) -> bool:
        return len(self.get_nodes(node_type)) > 0

    def get_nodes(self, node_type: Type[TNode]) -> Sequence[TNode]:
        return [node for node in self.nodes if isinstance(node, node_type)]

    def get_nodes_of(self, node_types: Tuple[Type[DynamoNode], ...], invert: bool = False) -> Sequence[DynamoNode]:
        return [node for node in self.nodes if isinstance(node, node_types) != invert]

    @property
    def is_unused(self) -> bool:
        return len(self.node_used_in()) == 0

    @property
    def has_dependency(self) -> bool:
        return len(self.dependencies) > 0

    @property
    def is_custom_node(self) -> bool:
        return self.file.name.lower().endswith("dyf")

    @property
    def is_script(self) -> bool:
        return self.file.name.lower().endswith("dyn")

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
        if len(nodes) == 0:
            return
        self.used_in.extend(nodes)

    @property
    def is_generated(self) -> bool:
        return self.file.name.startswith("Generate")

    def node_used_in(self) -> List[DynamoFile]:
        return sorted(self.used_in, key=lambda ele: ele.name)


@dataclass
class ScriptFile(DynamoFile):
    def add_used_in(self, _: Iterable[DynamoFile]) -> None:
        pass

    def node_used_in(self) -> List[DynamoFile]:
        return []
