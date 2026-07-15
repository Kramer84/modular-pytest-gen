from graphlib import CycleError, TopologicalSorter
from typing import Dict, List, Set


class DependencyGraph:
    r"""
    Construct a dependency graph for project architecture.
    
    The DependencyGraph class provides a mechanism to model and analyze
    project dependencies. It allows for the addition of nodes representing
    target paths and their dependencies, and provides a method to retrieve
    the bottom-up order of dependencies.
    
    Attributes
    ----------
    graph : Dict[str, Set[str]]
        A dictionary representing the dependency graph where keys are
        target paths and values are sets of dependencies.
    
    Methods
    -------
    add_node :
        Add a node to the dependency graph.
    get_bottom_up_order :
        Retrieve the bottom-up order of dependencies.
    
    Raises
    ------
    ValueError
        Circular dependency detected in project architecture.
    
    Warnings
    --------
    This implementation does not support parallel edges or self-loops.
    
    See Also
    --------
    networkx.DiGraph :
        Alternative graph implementation for more advanced features.
    
    Notes
    -----
    The graph is represented as an adjacency list using a dictionary of
    sets for efficient membership testing and edge management.
    """

    def __init__(self):
        r"""
        Initialize a directed graph structure.
        
        Constructs an empty dictionary to store the graph, where keys are
        node identifiers and values are sets of connected nodes.
        
        Warnings
        --------
        This implementation does not support parallel edges or self-loops.
        
        See Also
        --------
        networkx.DiGraph :
            Alternative graph implementation for more advanced features.
        
        Notes
        -----
        The graph is represented as an adjacency list using a dictionary of
        sets for efficient membership testing and edge management.
        """

        self.graph: Dict[str, Set[str]] = {}

    def add_node(self, target_path: str, dependencies: List[str]):
        r"""
        Add a node to the dependency graph.
        
        This method adds a node to the dependency graph, initializing its
        dependencies if the node does not already exist.
        
        Parameters
        ----------
        target_path : str
            The path of the node to be added to the graph.
        dependencies : List[str]
            A list of paths that the target node depends on.
        
        Returns
        -------
        None
            The method does not return any value.
        
        See Also
        --------
        modular_pytest_gen.graph.DependencyGraph.remove_node :
            Remove a node from the dependency graph.
        """

        if target_path not in self.graph:
            self.graph[target_path] = set()
        self.graph[target_path].update(dependencies)

    def get_bottom_up_order(self) -> List[str]:
        r"""
        Retrieve the topological order of nodes in the project graph.
        
        This method computes the bottom-up order of nodes in the project
        graph using a topological sort. It ensures that dependencies are
        resolved before their dependents.
        
        Returns
        -------
        List[str]
            A list of node names in topological order.
        
        Raises
        ------
        ValueError
            If a circular dependency is detected in the project
            architecture.
        """

        sorter = TopologicalSorter()
        for node, edges in self.graph.items():
            sorter.add(node, *edges)
        try:
            return list(sorter.static_order())
        except CycleError as e:
            raise ValueError(
                f"Circular dependency detected in project architecture: {e}"
            )
