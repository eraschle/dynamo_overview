import argparse
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

import st_cytoscape as graph
import streamlit as st

from dyndep import service
from dyndep.folder_picker import folder_picker
from dyndep.models import CustomNodeFile, DynamoFile, ScriptFile
from dyndep.service import GraphElement


def _parse_arguments() -> Tuple[Path, Path]:
    parser = argparse.ArgumentParser(
        prog="Script / Custom Node Visualisation",
        description="Create dynamic visualisation of script / custom node relation.",
        epilog="Ein wenig BIM, BIM mit Bam, Bam",
    )
    parser.add_argument(
        "-s",
        "--scripts",
        help="Root directory where the scripts are saved.",
        required=True,
    )
    parser.add_argument(
        "-l",
        "--library",
        help="Root directory where the custom nodes are saved.",
        required=True,
    )
    args = parser.parse_args()
    return Path(args.scripts), Path(args.library)


st.set_page_config(
    page_title="Dynamo Overview",
    page_icon="./apps/overview/dynamo.png",
    layout="wide",
)

SCRIPT_PATH = "script_path"
LIBRARY_PATH = "library_path"


def input_data() -> Tuple[Iterable[ScriptFile], Iterable[CustomNodeFile]]:
    col_left, col_right = st.columns(2)
    folder_picker(
        col_left,
        title="Skripts Folder",
        key="btn_scripts",
        state_key=SCRIPT_PATH,
    )
    folder_picker(
        col_right,
        title="Library Folder",
        key="btn_custom",
        state_key=LIBRARY_PATH,
    )
    if st.session_state.get(SCRIPT_PATH) is None or st.session_state.get(LIBRARY_PATH) is None:
        return ([], [])
    return service.script_n_custom_nodes(
        Path(st.session_state[SCRIPT_PATH]),
        Path(st.session_state[LIBRARY_PATH]),
    )


DEPENDENCY_STR = "Dependency"
USED_IN_STR = "Used in"
NODE_LENGTH = ">20"


def _node_name(node: DynamoFile) -> str:
    return f"{node.name:>50}"


def _display_normal(node: DynamoFile, depend_count: int) -> str:
    if isinstance(node, ScriptFile):
        return f"{_node_name(node)} ({DEPENDENCY_STR}: {depend_count})"
    used_count = len(node.node_used_in())
    return f"{_node_name(node)} ({DEPENDENCY_STR}: {depend_count} / {USED_IN_STR}: {used_count})"


def _display_dependency(node: DynamoFile, depend_count: int) -> str:
    return f"{_node_name(node)} ({DEPENDENCY_STR}: {depend_count})"


def _display_used_in(node: DynamoFile) -> str:
    used_count = len(node.node_used_in())
    return f"{_node_name(node)} ({USED_IN_STR}: {used_count})"


def _get_dependency_count(node: DynamoFile, library_uuid: Set[str]) -> int:
    unique_uuid = set(node.dependencies)
    dependencies = [uuid for uuid in unique_uuid if uuid in library_uuid]
    return len(dependencies)


def _node_display(node: DynamoFile, library_uuid: Set[str]) -> str:
    dependencies = _get_dependency_count(node, library_uuid)
    if st.session_state[SORT_KEY] == SORT_DEPENDENCY:
        return _display_dependency(node, dependencies)
    if st.session_state[SORT_KEY] == SORT_USED_IN:
        return _display_used_in(node)
    return _display_normal(node, dependencies)


def _show_in_selection(node: DynamoFile, library_uuid: Iterable[str]):
    if len(node.node_used_in()) > 0:
        return True
    return any(uuid in library_uuid for uuid in node.dependencies)


SCRIPT_TYPE = "Scripts"
CUSTOM_TYPE = "Custom Nodes"
SELECT_TYPE_KEY = "select_node_type"


def add_node_type_radio(script: Iterable[ScriptFile], custom: Iterable[CustomNodeFile]) -> Iterable[DynamoFile]:
    node_type = st.radio(
        label="Select type.",
        options=[SCRIPT_TYPE, CUSTOM_TYPE],
        key=SELECT_TYPE_KEY,
        horizontal=True,
    )
    return script if node_type == SCRIPT_TYPE else custom


def sort_node_name(node: DynamoFile) -> str:
    return node.name


def sort_file_name(node: DynamoFile) -> str:
    return node.path.name


def sort_dependency(node: DynamoFile) -> int:
    return len(node.dependencies)


def sort_used_in(node: DynamoFile) -> int:
    return len(node.node_used_in())


SORT_NODE_NAME = "Node-Name"
SORT_FILE_NAME = "File-Name"
SORT_DEPENDENCY = "Count Dependency"
SORT_USED_IN = "Count Used in"
SORT_KEY = "sort_selection"


def _sort_function(sort: Optional[str]) -> Tuple[Callable[[DynamoFile], Union[int, str]], bool]:
    if sort == SORT_FILE_NAME:
        return sort_file_name, False
    if sort == SORT_DEPENDENCY:
        return sort_dependency, True
    if sort == SORT_USED_IN:
        return sort_used_in, True
    return sort_node_name, False


def _get_sort_options() -> List[str]:
    options = [SORT_NODE_NAME, SORT_FILE_NAME, SORT_DEPENDENCY]
    if st.session_state[SELECT_TYPE_KEY] == CUSTOM_TYPE:
        options.append(SORT_USED_IN)
    return options


def add_node_sort_radio(nodes: Iterable[DynamoFile]) -> List[DynamoFile]:
    if nodes is None:
        return []
    sort_func = st.radio(
        label="Sorting.",
        options=_get_sort_options(),
        horizontal=True,
        key=SORT_KEY,
    )
    sort_func, reverse = _sort_function(sort_func)
    return sorted(nodes, key=sort_func, reverse=reverse)


def add_node_sort_and_type(column, script: Iterable[ScriptFile], custom: Iterable[CustomNodeFile]) -> List[DynamoFile]:
    with column:
        nodes = add_node_type_radio(script, custom)
        return add_node_sort_radio(nodes)


def add_selection_box(column, nodes: Iterable[DynamoFile], library: Iterable[CustomNodeFile]):
    library_uuid = set([node.uuid for node in library])
    selection_nodes = [node for node in nodes if _show_in_selection(node, library_uuid)]
    with column:
        selected = st.selectbox(
            label="Show Information for?",
            options=selection_nodes,
            format_func=lambda node: _node_display(node, library_uuid),
            placeholder="Select Script or Custom node...",
        )
        return selected


def _get_node(node: DynamoFile, selectable: bool) -> Dict[str, Any]:
    print(node)
    return {
        "data": {
            "id": node.uuid,
            "name": node.name,
            "color": "cyan" if isinstance(node, CustomNodeFile) else "green",
            "shape": "rectangle" if isinstance(node, CustomNodeFile) else "round-tag",
        },
        "selected": False,
        "selectable": selectable,
    }


def _get_graph_nodes(element: GraphElement) -> List[Dict[str, Any]]:
    elements = [_get_node(element.node, selectable=False)]
    for dep in element.dependencies:
        elements.append(_get_node(dep, selectable=True))
    for used in element.used_in:
        elements.append(_get_node(used, selectable=True))
    return elements


def _get_node_style() -> Dict[str, Any]:
    return {
        "selector": "node",
        "style": {
            "label": "data(name)",
            "width": 20,
            "height": 20,
            "background-color": "data(color)",
            "shape": "data(shape)",
            "font-size": 10,
            "text-valign": "center",
        },
    }


def _get_edge(source: DynamoFile, target: DynamoFile) -> Dict[str, Any]:
    return {
        "data": {
            "source": source.uuid,
            "target": target.uuid,
            "id": f"{source.uuid} -> {target.uuid}",
        },
        "selected": False,
        "selectable": False,
    }


def _get_graph_edge(element: GraphElement) -> List[Dict[str, Any]]:
    elements = []
    for dep in element.dependencies:
        elements.append(_get_edge(element.node, dep))
    for used in element.used_in:
        elements.append(_get_edge(used, element.node))
    return elements


def _get_edge_style() -> Dict[str, Any]:
    return {
        "selector": "edge",
        "style": {
            "width": 1,
            "curve-style": "round-taxi",
            "target-arrow-shape": "triangle",
        },
    }


def _get_graph_style() -> List[Dict[str, Any]]:
    return [_get_node_style(), _get_edge_style()]


def _get_graph_layout() -> Dict[str, Any]:
    return {
        "name": "fcose",
    }


def _get_elements(selected: Optional[DynamoFile], library: Iterable[CustomNodeFile]) -> List[Dict[str, Any]]:
    if selected is None:
        return []
    element = service.graph_elements(selected, library)
    return _get_graph_nodes(element) + _get_graph_edge(element)


def _get_graph(column, node: Optional[DynamoFile], library: Iterable[CustomNodeFile]) -> Optional[DynamoFile]:
    if node is None:
        return None
    nodes = [node, *library, *node.node_used_in()]
    print(f"Nodes: {nodes}")
    node_dict = {node.uuid: node for node in nodes}
    with column:
        selected = graph.cytoscape(
            elements=_get_elements(node, library),
            stylesheet=[_get_node_style(), _get_edge_style()],
            layout=_get_graph_layout(),
            selection_type="single",
            user_panning_enabled=True,
            user_zooming_enabled=True,
            key="graph",
        )
        selected_nodes = selected.get("nodes", [])
        if len(selected_nodes) == 0:
            return None
        return node_dict.get(selected_nodes[0])


def _get_detail(column, node: Optional[DynamoFile]) -> None:
    if node is None:
        return
    with column:
        detail = st.container(border=True)
        detail.subheader(node.name)
        detail.text(node.sub_path)
        for code in node.nodes:
            exp = detail.expander(code.name)
            exp.code(code.code)


def init_graph():
    scripts, library = input_data()
    col_left, col_right = st.columns(2)
    nodes = add_node_sort_and_type(col_left, scripts, library)
    root_node = add_selection_box(col_left, nodes, library)
    selected_node = _get_graph(col_left, root_node, library)
    _get_detail(col_right, selected_node)


if __name__ == "__main__":
    init_graph()
