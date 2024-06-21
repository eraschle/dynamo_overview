from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Type, TypeVar

from dyndep import builder
from dyndep.models import CustomNodeFile, DynamoFile, ScriptFile

TNode = TypeVar("TNode", bound=DynamoFile)


def _node_dict(nodes: Iterable[TNode], node_type: Type[TNode]) -> Dict[str, List[TNode]]:
    node_dict: Dict[str, List[node_type]] = {}
    for node in nodes:
        if node.uuid not in node_dict:
            node_dict[node.uuid] = []
        node_dict[node.uuid].append(node)
    return node_dict


def _print_not_unique_nodes(node_dict: Dict[str, List[TNode]]) -> None:
    not_unique = {uuid: nodes for uuid, nodes in node_dict.items() if len(nodes) > 1}
    if len(not_unique) == 0:
        return
    nodes = [f"{uuid} exists {len(nodes)} times" for uuid, nodes in not_unique.items()]
    print("\n".join(nodes))


def _unique_custom(custom_dict: Dict[str, List[CustomNodeFile]]) -> Dict[str, CustomNodeFile]:
    return {uuid: nodes[0] for uuid, nodes in custom_dict.items() if len(nodes) == 1}


def _custom_dict(path: Path) -> Dict[str, List[CustomNodeFile]]:
    nodes = builder.get_custom_file_nodes(path)
    return _node_dict(nodes, CustomNodeFile)


def _get_custom_node_dict(path: Path) -> Dict[str, CustomNodeFile]:
    custom_dict = _custom_dict(path)
    _print_not_unique_nodes(custom_dict)
    return _unique_custom(custom_dict)


def add_used_in(scripts: Iterable[DynamoFile], custom_nodes: Iterable[DynamoFile]) -> None:
    all_nodes = list(scripts)
    all_nodes.extend(custom_nodes)
    for node in custom_nodes:
        node.add_used_in(all_nodes)
    for script in scripts:
        script.add_used_in(all_nodes)


def script_file_dict(path: Path) -> Dict[str, ScriptFile]:
    scripts = builder.get_script_nodes(path)
    script_dict = _node_dict(scripts, ScriptFile)
    _print_not_unique_nodes(script_dict)
    return {script.uuid: script for script in scripts}


def script_n_custom_nodes(script: Path, custom: Path) -> Tuple[Iterable[ScriptFile], Iterable[CustomNodeFile]]:
    custom_dict = _get_custom_node_dict(custom)
    scripts = builder.get_script_nodes(script)
    add_used_in(scripts, custom_dict.values())
    return scripts, custom_dict.values()


@dataclass
class GraphElement:
    node: DynamoFile
    dependencies: List[DynamoFile]
    used_in: List[DynamoFile]


def dependency_of(source: DynamoFile, library: Iterable[CustomNodeFile]) -> List[DynamoFile]:
    return [node for node in library if node.uuid in source.dependencies]


def graph_elements(source: DynamoFile, library: Iterable[CustomNodeFile]) -> GraphElement:
    dependencies = dependency_of(source, library)
    return GraphElement(source, dependencies, source.node_used_in())
