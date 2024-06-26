from dataclasses import dataclass
from typing import Collection, Dict, Iterable, List, Optional, Tuple, Type, TypeVar

from dyndep import builder
from dyndep.models import CustomNodeFile, DynamoFile, DynFile, ScriptFile

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
    # nodes = [f"{uuid} exists {len(nodes)} times" for uuid, nodes in not_unique.items()]
    # print("\n".join(nodes))


def _unique_custom(custom_dict: Dict[str, List[CustomNodeFile]]) -> Dict[str, CustomNodeFile]:
    return {uuid: nodes[0] for uuid, nodes in custom_dict.items() if len(nodes) == 1}


def _is_custom_file(path: DynFile) -> bool:
    return path.name.lower().endswith("dyf")


def are_custom_nodes_in(paths: Optional[Iterable[DynFile]]) -> bool:
    if paths is None:
        return False
    return any(_is_custom_file(path) for path in paths)


def _get_node_files(paths: Iterable[DynFile]) -> Iterable[DynFile]:
    return [path for path in paths if _is_custom_file(path)]


def _custom_dict(files: Iterable[DynFile]) -> Dict[str, List[CustomNodeFile]]:
    files = _get_node_files(files)
    nodes = builder.get_custom_file_nodes(files)
    return _node_dict(nodes, CustomNodeFile)


def _get_custom_node_dict(files: Iterable[DynFile]) -> Dict[str, CustomNodeFile]:
    custom_dict = _custom_dict(files)
    _print_not_unique_nodes(custom_dict)
    return _unique_custom(custom_dict)


def add_used_in(scripts: Iterable[DynamoFile], custom_nodes: Iterable[DynamoFile]) -> None:
    all_nodes = list(scripts)
    all_nodes.extend(custom_nodes)
    for node in custom_nodes:
        node.add_used_in(all_nodes)
    for script in scripts:
        script.add_used_in(all_nodes)


def _is_script_file(path: DynFile) -> bool:
    return path.name.lower().endswith("dyn")


def are_scripts_in(files: Optional[Iterable[DynFile]]) -> bool:
    if files is None:
        return False
    return any(_is_script_file(path) for path in files)


def _get_script_files(files: Iterable[DynFile]) -> Iterable[DynFile]:
    return [path for path in files if _is_script_file(path)]


def script_file_dict(files: Iterable[DynFile]) -> Dict[str, ScriptFile]:
    files = _get_script_files(files)
    scripts = builder.get_script_nodes(files)
    script_dict = _node_dict(scripts, ScriptFile)
    _print_not_unique_nodes(script_dict)
    return {script.uuid: script for script in scripts}


def _is_dynamo_file(file: DynFile) -> bool:
    return _is_script_file(file) or _is_custom_file(file)


def script_n_custom_nodes(files: Iterable[DynFile]) -> Tuple[Collection[ScriptFile], Collection[CustomNodeFile]]:
    files = [file for file in files if _is_dynamo_file(file)]
    custom_dict = _get_custom_node_dict(files)
    scripts = builder.get_script_nodes(files)
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
