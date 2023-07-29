class StaticMemoryAllocation():

    def __init__(self, global_vars: dict(), changedNames = {}) -> None:
        self.__global_vars = global_vars
        self.__return_var = []
        self.__changedNames = {value:key for key, value in changedNames.items()}

    def generate(self):
        self.__return_var.append('; Allocating Global (static) memory')
        for n in self.__global_vars:
            if self.hasValue(n): var = n[0]; value = n[1]
            else: var = n

            # EQUATE
            firstChar = var[0]
            if self.canEquate(firstChar, n):
                print(f'{str(var+":"):<9}\t.EQUATE {value}', end = "") # reserving memory
        
            # WORD
            elif self.hasValue(n):
                instr = 'WORD'
                if len(n) == 3 and n[2] == 'list': instr = 'BLOCK'
                print(f'{str(var+":"):<9}\t.{instr} {value}', end = "\t")

            # BLOCK
            elif var: 
                print(f'{str(var+":"):<9}\t.BLOCK 2', end = "") # reserving memory
            
            # check if the variable name is in the changed names
            if var in self.__changedNames:
                print(f'\t;local variable {self.__changedNames[var]} #2d')
            elif self.hasValue(n) and len(n)==3 and n[2] == 'list':
                print(';list variable')
            else:
                print('\t;global variable #2d')

    # Check if the variable can be EQUATED
    def canEquate(self, firstChar, n):
        return firstChar.isupper() or firstChar == '_' and self.hasValue(n)
    
    # Check if the variable has a value
    def hasValue(self, n):
        return isinstance(n, tuple)
