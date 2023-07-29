class DynamicMemoryAllocation:
    def __init__(self, gloabal_vars):
        self.__local_vars = gloabal_vars
        self.__return_var = []

    def generate(self):

        self.__return_var.append('; Allocating local (dynamic) memory')
        address = 0

        # first allocate the local variables
        for n in self.__local_vars:
            if self.__local_vars[n] == 'local':
                self.__return_var.append(f'{str(n+":"):<9}\t.EQUATE {address}\t;local variable #2d')
                address = address + 2

        # allocate space for retAddr
        address += 2
        
        # allocate space for the parameters
        for n in self.__local_vars:
            if self.__local_vars[n] == 'param':
                self.__return_var.append(f'{str(n+":"):<9}\t.EQUATE {address}\t;formal parameter #2d')
                address = address + 2

        # allocate space for the return value
        for n in self.__local_vars:
            if self.__local_vars[n] == 'return':
                self.__return_var.append(f'{str(n+":"):<9}\t.EQUATE {address}\t;return parameter #2d')
                address = address + 2
        
        # print the generated code
        self.print_generate()
        
    def print_generate(self):
        if len(self.__return_var) == 1: self.__return_var = []
        for line in self.__return_var:
            print(line)
