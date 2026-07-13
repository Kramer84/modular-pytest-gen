from graphlib import CycleError, TopologicalSorter
from typing import Dict, List, Set


class DependencyGraph:
    def __init__(self):
        self.graph: Dict[str, Set[str]] = {}

    def add_node(self, target_path: str, dependencies: List[str]):
        if target_path not in self.graph:
            self.graph[target_path] = set()
        self.graph[target_path].update(dependencies)

    def get_bottom_up_order(self) -> List[str]:
        sorter = TopologicalSorter()
        for node, edges in self.graph.items():
            sorter.add(node, *edges)
        try:
            return list(sorter.static_order())
        except CycleError as e:
            raise ValueError(
                f"Circular dependency detected in project architecture: {e}"
            )
