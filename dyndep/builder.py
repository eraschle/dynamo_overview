import json
from typing import Any, Dict, Iterable, List, Optional

from dyndep import content_builder as node
from dyndep.models import Annotation, CustomNode, CustomNodeFile, DynamoNode, DynFile, Package, ScriptFile


def _get_file_content(file: DynFile) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(file.getvalue())
    except json.JSONDecodeError:
        print(f"Error in {file.name} ({file.file_id}) {file.type}")
        return None


def _file_node_uuid(content: Dict[str, Any]) -> str:
    uuid = content.get("Uuid", None)
    if uuid is None:
        raise Exception("Content has no UUID")
    return uuid


def _get_packages(file_content: Dict[str, Any]) -> Dict[str, Package]:
    package_dict = {}
    builder = node.package_builder()
    for content in file_content.get("NodeLibraryDependencies", []):
        if not builder.is_builder_for(content):
            continue
        package = builder.build(content)
        package_dict.update(
            {node_id: package for node_id in builder.get_node_ids(content)},
        )
    return package_dict


def _get_node_view_dict(file_content: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    view_dict = {}
    for view in file_content.get("View", {}).get("NodeViews", []):
        node_id = node.get_node_id(view)
        view_dict[node_id] = view
    return view_dict


def _add_package(node: DynamoNode, packages: Dict[str, Package]) -> DynamoNode:
    if isinstance(node, CustomNode) and node.uuid in packages:
        node.package = packages[node.uuid]
    return node


def _get_nodes(file_content: Dict[str, Any]) -> List[DynamoNode]:
    if "View" not in file_content:
        return []
    nodes = []
    view_dict = _get_node_view_dict(file_content)
    package_dict = _get_packages(file_content)
    for content in file_content.get("Nodes", []):
        builder = node.node_builder(content)
        content_node = builder.build(content, view_dict)
        content_node = _add_package(content_node, package_dict)
        nodes.append(content_node)
    return nodes


def _get_groups(file_content: Dict[str, Any], nodes: Iterable[DynamoNode]) -> List[Annotation]:
    groups = file_content.get("Annotations", [])
    if len(groups) == 0:
        return []
    builder = node.annotion_builder()
    return [builder.build(grp, nodes) for grp in groups]


def _node_dependencies(content: Dict[str, Any]) -> List[str]:
    dependencies = content.get("Dependencies", [])
    return dependencies


def _custom_categories(content: Dict[str, Any]) -> List[str]:
    category = content.get("Category", "")
    if len(category) == 0:
        return []
    return category.split(".")


def _create_custom_node(file: DynFile) -> Optional[CustomNodeFile]:
    content = _get_file_content(file)
    if content is None:
        return None
    nodes = _get_nodes(content)
    return CustomNodeFile(
        uuid=_file_node_uuid(content),
        name=node.get_node_name(content),
        file=file,
        nodes=nodes,
        categories=_custom_categories(content),
        dependencies=_node_dependencies(content),
        groups=_get_groups(content, nodes),
    )


def get_custom_file_nodes(files: Iterable[DynFile]) -> List[CustomNodeFile]:
    nodes = [_create_custom_node(file) for file in files]
    return [node for node in nodes if node is not None]


def _create_script(file: DynFile) -> Optional[ScriptFile]:
    content = _get_file_content(file)
    if content is None:
        return None
    nodes = _get_nodes(content)
    return ScriptFile(
        uuid=_file_node_uuid(content),
        name=node.get_node_name(content),
        file=file,
        nodes=nodes,
        dependencies=_node_dependencies(content),
        groups=_get_groups(content, nodes),
    )


def get_script_nodes(files: Iterable[DynFile]) -> List[ScriptFile]:
    scripts = [_create_script(file) for file in files]
    return [node for node in scripts if node is not None]
