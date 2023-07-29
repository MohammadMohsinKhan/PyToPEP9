import ast

class LocalVariableExtraction(ast.NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.__instructions = list()
        self.__should_save = True
        self.__elem_id = 0
        self.__current_variable = None
        self.visited = {}
        self.vars = {}
        self.__local_vars = {}
        self.__nlocal_vars = 0
        self.__functionMemory = {}

    # return the function instructions
    def finalize(self):
        return self.__instructions

    # returns the local variables
    def getLocalVars(self):
        return self.__local_vars

    def __record_instruction(self, instruction, label = None):
        self.__instructions.append((label, instruction))

    def __access_memory(self, node, instruction, label = None):
        if isinstance(node, ast.Constant):
            val, call_type = node.value, 'i'
        elif self.is_subscript(node):
            val, call_type = node.slice.id, 's'
        else:
            val, call_type = node.id, 's'
            if node.id[0] == "_": val, call_type = node.id, 'i'
        self.__record_instruction(f'{instruction} {val},{call_type}', label)

    def __identify(self):
        result = self.__elem_id
        self.__elem_id = self.__elem_id + 1
        return result

    # visit the function body
    def visit_FunctionDef(self, node):
        self.__functionMemory[node.name] = 0
        functionParams = node.args.args

        #add the parameters to the local variables dictionary
        for param in functionParams:
            self.__local_vars[param.arg] = "param"
            self.__functionMemory[node.name] += 1

        #check if there is a return statement and add 2 to the function memory
        for statement in node.body:
            if isinstance(statement, ast.Return):
                self.__functionMemory[node.name] += 1
                break

        # call the function that counts the number of local variables for memory allocation
        self.countLocalVars(node)

        self.__instructions.append((node.name, "NOP1"))
        self.__record_instruction("SUBSP " + str(2 * self.__nlocal_vars) + ",i")

        # visit the function body contents
        for content in node.body:
            self.visit(content)

        self.__record_instruction("ADDSP " + str(2 * self.__nlocal_vars) + ",i")
        self.__nlocal_vars = 0
        self.__instructions.append((None, 'RET'))
        

    def visit_Assign(self, node):
        target = node.targets[0]
        value_target = node.value
        if isinstance(target, ast.Subscript):
            self.__current_variable = target.value.id
        # remembering the name of the target
        else: self.__current_variable = target.id

        
        # visiting the left part, now knowing where to store the result
        self.visit(value_target)
        if self.is_subscript(target): self.visit(target)
        # if List, should not save
        if isinstance(value_target, ast.BinOp) and self.is_list(value_target.left):
            self.__should_save = False
        # remove instruction if we later know it's EQUATE
        if self.__should_save and self.__current_variable[0] != "_" and self.__current_variable[-1] != "_":
            self.__record_instruction(f'STWA {self.__current_variable},s')
        else:
            self.__should_save = True
        self.__current_variable = None

    ## check if variable is extra, if so remove it
    
    def checkExtra(self,node):
        if self.__current_variable not in self.vars:
            self.vars[self.__current_variable] = []
        self.vars[self.__current_variable].append(f'LDWA {node.value},i')

        for var in self.vars:
            if len(self.vars[var]) > 1:
                indexOfRemoved = self.__instructions.index((None, self.vars[var][0]))
                del self.__instructions[indexOfRemoved+1]
                del self.__instructions[indexOfRemoved]

    def visit_Constant(self, node):
        self.checkExtra(node)

        # if constant then use variable
        if self.__current_variable[0] == "_":
            return
        else: self.__record_instruction(f'LDWA {node.value},i')

    
    def visit_Name(self, node):
        self.__record_instruction(f'LDWA {node.id},s')

    def visit_BinOp(self, node):
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
                self.__record_instruction(f'DECI {self.__current_variable},s')
                self.__should_save = False
            case 'print':
                if isinstance(node.args[0], ast.Subscript):
                    self.__record_instruction(f'LDWX {node.args[0].slice.id},s')
                    self.__record_instruction("ASLX")
                    self.__record_instruction(f'DECO {node.args[0].value.id},x')
                else: self.__record_instruction(f'DECO {node.args[0].id},s')
            case 'exit':
                self.__record_instruction('STOP')
            # make a case for a function call
            case _:
                if self.__functionMemory[node.func.id] != 0:
                    self.__record_instruction("STWA " + str(-2 * self.__functionMemory[node.func.id]) + ",s")
                    self.__record_instruction("SUBSP " + str(2 * self.__functionMemory[node.func.id]) + ",i")
                    self.__record_instruction("CALL " + node.func.id)
                    self.__record_instruction("ADDSP " + str(2 * self.__functionMemory[node.func.id]) + ",i")
                    self.__record_instruction("LDWA " + str(-2) + ",s")


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
        if self.is_subscript(node.test.left): 
            self.__access_memory(node.test.left, 'LDWX', label = f'if_{if_id}')
            self.__record_instruction('ASLX')
            self.__record_instruction(f'LDWA {node.test.left.value.id},x')
        else: self.__access_memory(node.test.left, 'LDWA', label = f'if_{if_id}')
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

    # Function to count the number of local variables in a function
    def countLocalVars(self, node):
        for content in node.body:
            cont_flag = False
            
            if self.is_assign(content):
                target = content.targets[0]
                cont_flag = True
            try:
                if self.is_subscript(content.targets[0]):
                    target = content.targets[0].value
                    cont_flag = True
            except: pass
            
            if cont_flag and self.is_store(target) and target.id not in self.__local_vars:
                self.__local_vars[target.id] = "local"
                self.__nlocal_vars += 1

            elif self.is_for(content) or self.is_while(content):
                self.countLocalVars(content)

            elif self.is_if(content):
                self.orelse_rec(content)
    
    # Helper function for countLocalVars
    def orelse_rec(self, node):
        for orelse in node.orelse:
            if self.is_assign(orelse):
                target = orelse.targets[0]
                if self.is_store(target) and target.id not in self.__local_vars:
                    self.__local_vars[target.id] = "local"
                    self.__nlocal_vars += 1

            elif self.is_for(orelse) or self.is_while(orelse) or self.is_if(orelse):
                self.orelse_rec(orelse)

    def visit_Return(self, node):
        counter = 0
        val = node.value
        call_type = 's'
        if self.is_subscript(val): val = val.value; call_type = 'x'
        self.__record_instruction(f'LDWA {val.id},{call_type}')
        self.__record_instruction("STWA " + "ret" + val.id[:3]+ ",s")
        if ("ret" + val.id[:3] not in self.__local_vars):
            self.__local_vars["ret" + val.id[:3]] = "return"
        else:
            self.__local_vars["ret" + val.id[:2] + str(counter)] =  "return"
            counter += 1

    def visit_Subscript(self, node):
        index = node.slice.id
        var = node.value.id
        self.__record_instruction(f'LDWX {index},s')
        self.__record_instruction(f'ASLX')
        self.__record_instruction(f'STWA {var},x')

    # function to check if the node is a while loop
    def is_while(self, node):
        return isinstance(node, ast.While)
    
    # function to check if the node is an if statement
    def is_if(self, node):
        return isinstance(node, ast.If)

    # function to check if the node is a for loop
    def is_for(self, node):
        return isinstance(node, ast.For)

    # function to check if the node is an assignment
    def is_assign(self, node):
        return isinstance(node, ast.Assign)
    
    # function to check if the node is a store
    def is_store(self, node):
        return isinstance(node.ctx, ast.Store)
    
    # function to check if the node is a subscript
    def is_subscript(self, node):
        return isinstance(node, ast.Subscript)
    
    # function to check if the node is a list
    def is_list(self, node):
        return isinstance(node, ast.List)