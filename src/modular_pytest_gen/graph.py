from graphlib import TopologicalSorter, CycleError
from typing import Dict, List, Set

class DependencyGraph:
    """
    Constructs a project-wide Directed Acyclic Graph (DAG) of function dependencies
    and calculates the bottom-up topological sort for docstring generation.
    """
    def __init__(self):
        # Maps a globally unique function path to its set of dependencies
        # e.g., {'otaf.capabilities.process_capability': {'otaf.common.validate_dict_keys'}}
        self.graph: Dict[str, Set[str]] = {}
        
    def add_node(self, target_path: str, dependencies: List[str]):
        """Registers a function and the internal project functions it calls."""
        if target_path not in self.graph:
            self.graph[target_path] = set()
        self.graph[target_path].update(dependencies)

    def get_bottom_up_order(self) -> List[str]:
        """
        Calculates the execution order. Leaf nodes (functions with no internal 
        dependencies) will be returned first.
        """
        sorter = TopologicalSorter()
        
        for node, edges in self.graph.items():
            # TopologicalSorter expects (node, *predecessors)
            sorter.add(node, *edges)
            
        try:
            # static_order() returns the resolution from leaf nodes up to root nodes
            return list(sorter.static_order())
        except CycleError as e:
            raise ValueError(f"Circular dependency detected in project architecture: {e}")