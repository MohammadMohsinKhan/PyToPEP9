import ast

class GlobalVariableExtraction(ast.NodeVisitor):
    """ 
        We extract all the left hand side of the global (top-level) assignments
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.results = set()
        self.visited = {}

    def visit_Assign(self, node):
        # Initalize variables
        target = node.targets[0]
        nvalue = node.value

        if len(node.targets) != 1:
            raise ValueError("Only unary assignments are supported")

        # Skip the subscript
        if self.isSubscript(target): return

        # Add list variable
        if self.isBinOp(nvalue) and self.isList(nvalue.left):
            self.results.add((target.id, nvalue.right.value*2,"list"))
            return
        
        # Add variable
        if node.targets[0].id in self.visited: return
        self.visited[target.id] = (target.id)

        # Add constant
        if self.isConstant(nvalue):
            self.results.add((target.id, node.value.value))
        else: self.results.add(target.id)
        
    def visit_FunctionDef(self, node):
        """We do not visit function definitions, they are not global by definition"""
        pass

    """Helper functions"""
    def isBinOp(self, node):
        return isinstance(node, ast.BinOp)
    
    def isList(self, node):
        return isinstance(node, ast.List)

    def isSubscript(self, node):
        return isinstance(node, ast.Subscript)

    def isConstant(self, node):
        return isinstance(node, ast.Constant)
