import json
from typing import Any, Dict, Iterable, List

from altair import Optional

from dyndep.models import CodeNode, CustomNodeFile, DynFile, ScriptFile


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


def _get_node_name(content: Dict[str, Any]) -> str:
    name = content.get("Name", None)
    if name is None:
        raise Exception("Content has no Name")
    return name


def _get_node_id(content: Dict[str, Any]) -> str:
    node_id = content["Id"]
    if node_id is None:
        raise Exception(f"{content} has no ID")
    return node_id


CODE_NODES = {
    "ConcreteType": "PythonNodeModels.PythonNode, PythonNodeModels",
    "NodeType": "PythonScriptNode",
}


def _is_code_node(content: Dict[str, Any]) -> bool:
    return all(content.get(key, None) == value for key, value in CODE_NODES.items())


def _get_node_view_dict(file_content: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    view_dict = {}
    for view in file_content.get("View", {}).get("NodeViews", []):
        node_id = _get_node_id(view)
        view_dict[node_id] = view
    return view_dict


def _create_code_node(node_content: Dict[str, Any], view_dict: Dict[str, Dict[str, Any]]) -> CodeNode:
    node_id = _get_node_id(node_content)
    if node_id not in view_dict:
        raise Exception(f"No Node View for {node_id}")
    return CodeNode(
        uuid=node_id,
        name=_get_node_name(view_dict[node_id]),
        code=node_content["Code"],
        engine=node_content.get("Engine", "IronPython2"),
    )


def _get_code_nodes(file_content: Dict[str, Any]) -> List[CodeNode]:
    if "View" not in file_content:
        return []
    nodes = []
    view_dict = _get_node_view_dict(file_content)
    for content in file_content.get("Nodes", []):
        if not _is_code_node(content):
            continue
        nodes.append(_create_code_node(content, view_dict))
    return nodes


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
    return CustomNodeFile(
        uuid=_file_node_uuid(content),
        name=_get_node_name(content),
        file=file,
        categories=_custom_categories(content),
        dependencies=_node_dependencies(content),
        nodes=_get_code_nodes(content),
    )


def get_custom_file_nodes(files: Iterable[DynFile]) -> List[CustomNodeFile]:
    nodes = [_create_custom_node(file) for file in files]
    return [node for node in nodes if node is not None]


def _create_script(file: DynFile) -> Optional[ScriptFile]:
    content = _get_file_content(file)
    if content is None:
        return None
    return ScriptFile(
        uuid=_file_node_uuid(content),
        name=_get_node_name(content),
        file=file,
        dependencies=_node_dependencies(content),
        nodes=_get_code_nodes(content),
    )


def get_script_nodes(files: Iterable[DynFile]) -> List[ScriptFile]:
    scripts = [_create_script(file) for file in files]
    return [node for node in scripts if node is not None]
