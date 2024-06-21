import codecs
import json
from pathlib import Path
from typing import Any, Dict, List

from dyndep.models import CodeNode, CustomNodeFile, ScriptFile


def _get_file_content(path: Path) -> Dict[str, Any]:
    with codecs.open(str(path), mode="r", encoding="utf-8") as file:
        return json.load(file)


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


def _create_custom_node(path: Path, root: Path) -> CustomNodeFile:
    content = _get_file_content(path)
    return CustomNodeFile(
        uuid=_file_node_uuid(content),
        name=_get_node_name(content),
        root_path=root,
        path=path,
        categories=_custom_categories(content),
        dependencies=_node_dependencies(content),
        nodes=_get_code_nodes(content),
    )


def get_custom_file_nodes(path: Path) -> List[CustomNodeFile]:
    nodes = []
    for node_path in path.rglob("*.dyf"):
        nodes.append(_create_custom_node(node_path, path))
    return nodes


def _create_script(path: Path, root: Path) -> ScriptFile:
    content = _get_file_content(path)
    return ScriptFile(
        uuid=_file_node_uuid(content),
        name=_get_node_name(content),
        root_path=root,
        path=path,
        dependencies=_node_dependencies(content),
        nodes=_get_code_nodes(content),
    )


def get_script_nodes(path: Path) -> List[ScriptFile]:
    scripts = []
    for script in path.rglob("*.dyn"):
        scripts.append(_create_script(script, path))
    return scripts
