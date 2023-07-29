import ast

LabeledInstruction = tuple[str, str]

class TopLevelProgram(ast.NodeVisitor):
    """We supports assignments and input/print calls"""
    
    def __init__(self, entry_point) -> None:
        super().__init__()
        self.__instructions = list()
        self.__record_instruction('NOP1', label=entry_point)
        self.__should_save = True
        self.__current_variable = None
        self.__elem_id = 0
        self.vars = {}
        self.__functionReturns = {}

    def finalize(self):
        self.__instructions.append((None, '.END'))
        return self.__instructions

    ####
    ## Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node):
        target = node.targets[0]
        value_target = node.value
        if isinstance(target, ast.Subscript):
            self.__current_variable = target.value.id
        # remembering the name of the target
        else: self.__current_variable = target.id

        
        # visiting the left part, now knowing where to store the result
        self.visit(value_target)
        if self.isSubscript(target): self.visit(target)
        # if List, should not save
        if isinstance(value_target, ast.BinOp) and isinstance(value_target.left, ast.List):
            self.__should_save = False
        # remove instruction if we later know it's EQUATE
        if self.__should_save and self.__current_variable[0] != "_" and not self.isSubscript(target):
            self.__record_instruction(f'STWA {self.__current_variable},d')
        else:
            self.__should_save = True
        self.__current_variable = None
    
    ## check if variable is extra, if so remove it
    def checkExtra(self,node):
        if self.__current_variable not in self.vars:
            self.vars[self.__current_variable] = []
        self.vars[self.__current_variable].append(f'LDWA {node.value},i')

        # if variable is extra, remove it
        for var in self.vars:
            if len(self.vars[var]) > 1:
                indexOfRemoved = self.__instructions.index((None, self.vars[var][0]))
                del self.__instructions[indexOfRemoved+1]
                del self.__instructions[indexOfRemoved]
                del self.vars[var][0]

    def visit_Constant(self, node):
        self.checkExtra(node)

        # if constant then use variable
        if self.__current_variable[0] == "_":
            return
        else: self.__record_instruction(f'LDWA {node.value},i')
    
    def visit_Name(self, node):
        self.__record_instruction(f'LDWA {node.id},d')

    def visit_BinOp(self, node):
        if isinstance(node.left, ast.List): return

        self.__access_memory(node.left, 'LDWA')
        if isinstance(node.op, ast.Add):
            self.__access_memory(node.right, 'ADDA')
        elif isinstance(node.op, ast.Sub):
            self.__access_memory(node.right, 'SUBA')
        else:
            raise ValueError(f'Unsupported binary operator: {node.op}')

    def visit_Call(self, node):
        match node.func.id:
            case 'int': 
                # Let's visit whatever is casted into an int
                self.visit(node.args[0])
            case 'input':
                # We are only supporting integers for now
                self.__record_instruction(f'DECI {self.__current_variable},d')
                self.__should_save = False # DECI already save the value in memory
            case 'print':
                if isinstance(node.args[0], ast.Subscript):
                    self.__record_instruction(f'LDWX {node.args[0].slice.id},d')
                    self.__record_instruction("ASLX")
                    self.__record_instruction(f'DECO {node.args[0].value.id},x')
                else: self.__record_instruction(f'DECO {node.args[0].id},d')
            case 'exit':
                self.__record_instruction('STOP')
            case _:
                nLocalVars = 0
                for arg in node.args:
                    nLocalVars += 1
                    self.__record_instruction(f'LDWA {arg.id},d')
                if (self.__current_variable is not None):
                    nLocalVars += 1

                # if void function, just call it
                if nLocalVars == 0:
                    self.__record_instruction(f'CALL {node.func.id}')
                    if (self.__functionReturns[node.func.id]):
                        self.__record_instruction("LDWA " + str(-2) + ",s")
                
                # else function has parameters
                else:
                    self.__record_instruction("STWA " + str(-2 * nLocalVars) + ",s")
                    self.__record_instruction("SUBSP " + str(2 * nLocalVars) + ",i")
                    self.__record_instruction("CALL " + node.func.id)
                    self.__record_instruction("ADDSP " + str(2 * nLocalVars) + ",i")
                    if (self.__functionReturns[node.func.id]):
                        self.__record_instruction("LDWA " + str(-2) + ",s")
                
                nLocalVars = 0
            

    ####
    ## Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node):
        loop_id = self.__identify()
        inverted = {
            ast.Lt:  'BRGE', # '<'  in the code means we branch if '>=' 
            ast.LtE: 'BRGT', # '<=' in the code means we branch if '>' 
            ast.Gt:  'BRLE', # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT', # '>=' in the code means we branch if '<'
            ast.Eq : 'BRNE', # '==' in the code means we branch if '!='
            ast.NotEq: 'BREQ', # '!=' in the code means we branch if '=='
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label = f'while_{loop_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true (thus, inverted)
        self.__record_instruction(f'{inverted[type(node.test.ops[0])]} end_l_{loop_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR while_{loop_id}')
        # Sentinel marker for the end of the loop
        self.__record_instruction(f'NOP1', label = f'end_l_{loop_id}')

    def visit_If(self, node):
        if_id = self.__identify()
        inverted = {
            ast.Lt:  'BRGE', # '<'  in the code means we branch if '>=' 
            ast.LtE: 'BRGT', # '<=' in the code means we branch if '>' 
            ast.Gt:  'BRLE', # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT', # '>=' in the code means we branch if '<'
            ast.Eq : 'BRNE', # '==' in the code means we branch if '!='
            ast.NotEq: 'BREQ', # '!=' in the code means we branch if '=='
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label = f'if_{if_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true (thus, inverted)
        self.__record_instruction(f'{inverted[type(node.test.ops[0])]} else_{if_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR end_{if_id}')
        # Sentinel marker for the else
        self.__record_instruction(f'NOP1', label = f'else_{if_id}')
        # Visiting the body of the else
        for contents in node.orelse:
            self.visit(contents)
        # Sentinel marker for the end of the if
        self.__record_instruction(f'NOP1', label = f'end_{if_id}')

    ####
    ## Not handling function calls 
    ####

    def visit_FunctionDef(self, node):
        flag = False
        for content in node.body:
            if (isinstance(content, ast.Return)):
                self.__functionReturns[node.name] = True
                flag = True

        if (not flag):
            self.__functionReturns[node.name] = False

    def visit_Subscript(self, node):
        index = node.slice.id
        var = node.value.id
        self.__record_instruction(f'LDWX {index},d')
        self.__record_instruction(f'ASLX')
        self.__record_instruction(f'STWA {var},x')

    ####
    ## Helper functions to 
    ####

    def __record_instruction(self, instruction, label = None):
        self.__instructions.append((label, instruction))

    def __access_memory(self, node, instruction, label = None):
        if isinstance(node, ast.Constant):
            self.__record_instruction(f'{instruction} {node.value},i', label)
        else:
            const = 'i' if (node.id[0] == '_') else 'd' # EQUATE uses i
            self.__record_instruction(f'{instruction} {node.id},{const}', label)

    def __identify(self):
        result = self.__elem_id
        self.__elem_id = self.__elem_id + 1
        return result

    def isSubscript(self, node):
        return isinstance(node, ast.Subscript)