import re
from abc import ABC, abstractmethod
import inspect
from typing import Any, Dict, List, Iterable, Type, TypeGuard

from dyndep.models import Annotation, CustomNode, DynamoNode, Package, PythonCodeNode, BaseNode


def get_node_id(content: Dict[str, Any]) -> str:
    node_id = content["Id"]
    if node_id is None:
        raise Exception(f"{content} has no ID")
    return node_id


def get_node_name(content: Dict[str, Any]) -> str:
    name = content.get("Name", None)
    if name is None:
        raise Exception("Content has no Name")
    return name


def _get_node_content(content: Dict[str, Any], views: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Node": content,
        "View": views.get(get_node_id(content)),
    }


def _get_node_type(content: Dict[str, Any]) -> str:
    return content.get("NodeType", "NO NODE TYPE")


def _get_concrete_type(content: Dict[str, Any]) -> str:
    return content.get("ConcreteType", "NO CONCRETE TYPE")


class NodeBuilder(ABC):
    @classmethod
    @abstractmethod
    def lookup(cls) -> Dict[str, Any]:
        pass

    @classmethod
    def is_node_value(cls, content: Dict[str, Any], key: str, value: Any) -> bool:
        return content.get(key, None) == value

    @classmethod
    def is_builder_for(cls, content: Dict[str, Any]) -> bool:
        return all(cls.is_node_value(content, key, value) for key, value in cls.lookup().items())

    def _node_id(self, node: Dict[str, Any], views: Dict[str, Any]) -> str:
        node_id = get_node_id(node)
        if node_id not in views:
            raise Exception(f"No Node View for {node_id}")
        return node_id

    @abstractmethod
    def build(self, node: Dict[str, Any], views: Dict[str, Any]) -> DynamoNode:
        pass


class DefaultNodeBuilder(NodeBuilder):
    @classmethod
    def lookup(cls) -> Dict[str, Any]:
        return {
            "ConcreteType": "",
            "NodeType": "",
        }

    @classmethod
    def is_node_value(cls, content: Dict[str, Any], key: str, _: Any) -> bool:
        return key in content

    def build(self, node: Dict[str, Any], views: Dict[str, Any]) -> DynamoNode:
        node_id = self._node_id(node, views)
        return DynamoNode(
            uuid=node_id,
            name=get_node_name(views[node_id]),
            content=_get_node_content(node, views),
            node_type=_get_node_type(node),
            concrete_type=_get_concrete_type(node),
            group=None,
        )


class CodeNodeBuilder(NodeBuilder):
    @classmethod
    def lookup(cls) -> Dict[str, Any]:
        return {
            "ConcreteType": "PythonNodeModels.PythonNode, PythonNodeModels",
            "NodeType": "PythonScriptNode",
        }

    def build(self, node: Dict[str, Any], views: Dict[str, Any]) -> DynamoNode:
        node_id = self._node_id(node, views)
        return PythonCodeNode(
            uuid=node_id,
            name=get_node_name(views[node_id]),
            content=_get_node_content(node, views),
            node_type=_get_node_type(node),
            concrete_type=_get_concrete_type(node),
            code=node["Code"],
            engine=node.get("Engine", "IronPython2"),
            group=None,
        )


GUID_PATTERN = re.compile("([a-zA-Z0-9]{8})-([a-zA-Z0-9]{4})-([a-zA-Z0-9]{4})-([a-zA-Z0-9]{4})-([a-zA-Z0-9]{12})")


class CustomNodeBuilder(NodeBuilder):
    @classmethod
    def lookup(cls) -> Dict[str, Any]:
        return {
            "ConcreteType": "Dynamo.Graph.Nodes.CustomNodes.Function, DynamoCore",
            "FunctionType": "Graph",
            "FunctionSignature": GUID_PATTERN,
        }

    @classmethod
    def is_node_value(cls, content: Dict[str, Any], key: str, value: Any) -> bool:
        content_value = content.get(key, None)
        if isinstance(value, re.Pattern):
            return value.match(content_value) is not None
        return content_value == value

    def build(self, node: Dict[str, Any], views: Dict[str, Any]) -> DynamoNode:
        node_id = self._node_id(node, views)
        return CustomNode(
            uuid=node_id,
            name=get_node_name(views[node_id]),
            content=_get_node_content(node, views),
            node_type=_get_node_type(node),
            concrete_type=_get_concrete_type(node),
            custom_uuid=node["FunctionSignature"],
            group=None,
            package=Package.default(),
        )


BUILDERS = []


def _is_default(builder: NodeBuilder) -> bool:
    if inspect.isabstract(builder) or not hasattr(builder, "lookup"):
        return False
    return all(len(val) == 0 for val in builder.lookup().values())


def _ensure_default_is_last(builders: List[NodeBuilder]) -> Iterable[NodeBuilder]:
    builder = [build for build in builders if _is_default(build)]
    if len(builder) != 1:
        raise Exception("Zero or more then one default builder found.")
    builders = [build for build in builders if not _is_default(build)]
    return builders + builder


def _is_builder(value: Any) -> TypeGuard[Type[NodeBuilder]]:
    if not inspect.isclass(value):
        return False
    if not issubclass(value, NodeBuilder):
        return False
    if inspect.isabstract(value):
        return False
    return True


def _create_builder() -> Iterable[NodeBuilder]:
    builders: List[NodeBuilder] = []
    for name, builder_type in globals().items():
        if "builder" not in name.lower() or not _is_builder(builder_type):
            continue
        builders.append(builder_type())
    return _ensure_default_is_last(builders)


def _get_builders() -> Iterable[NodeBuilder]:
    global BUILDERS
    if len(BUILDERS) == 0:
        BUILDERS = _create_builder()
    return BUILDERS


def node_builder(content: Dict[str, Any]) -> NodeBuilder:
    for builder in _get_builders():
        if not builder.is_builder_for(content):
            continue
        return builder
    message = f"No builder found for content\n{content}"
    raise Exception(message)


class AnnotationBuilder:
    def _group_nodes(self, content: Dict[str, Any], nodes: Iterable[BaseNode]) -> List[BaseNode]:
        group_node_ids = content.get("Nodes", [])
        group_nodes = [node for node in nodes if node.uuid in group_node_ids]
        return group_nodes

    def build(self, content: Dict[str, Any], nodes: Iterable[BaseNode]) -> Annotation:
        return Annotation(
            uuid=get_node_id(content),
            name=content["Title"],
            nodes=self._group_nodes(content, nodes),
            group=None,
            content=content,
        )


def annotion_builder() -> AnnotationBuilder:
    return AnnotationBuilder()


class PackageBuilder:
    @classmethod
    def lookup(cls) -> Dict[str, Any]:
        return {
            "ReferenceType": "Package",
        }

    @classmethod
    def is_node_value(cls, content: Dict[str, Any], key: str, value: Any) -> bool:
        return content.get(key, None) == value

    @classmethod
    def is_builder_for(cls, content: Dict[str, Any]) -> bool:
        return all(cls.is_node_value(content, key, value) for key, value in cls.lookup().items())

    def build(self, content: Dict[str, Any]) -> Package:
        return Package(
            name=get_node_name(content),
            version=content["Version"],
        )

    def get_node_ids(self, content: Dict[str, Any]) -> Iterable[str]:
        return content.get("Nodes", [])


def package_builder() -> PackageBuilder:
    return PackageBuilder()
