class EntryPoint():

    def __init__(self, instructions, varChanges = {}, isFunc = False) -> None:
        self.__instructions = instructions
        self.__varChanges = varChanges
        self.__isFunc = isFunc
        self.reNameGlobalVars()

    # if a gloabl variable name was changed in symbol table, change it in the instructions as well
    def reNameGlobalVars(self):
        if (not self.__isFunc):
            for i in range(len(self.__instructions)):
                var = self.__instructions[i]
                if (var[1] == "NOP1" or var[1] == ".END" or var[1]=="STOP" or var[1]=="ASLX"): continue
                varName = var[1].split(" ")[1].split(",")[0]
                if (varName in self.__varChanges):
                    self.__instructions[i] = list(var)
                    self.__instructions[i][1] = self.__instructions[i][1].replace(varName, self.__varChanges[varName])
                    self.__instructions[i] = tuple(self.__instructions[i])

    # Print instructions
    def generate(self):
        if not self.__isFunc:
            print('; Top Level instructions')

        for label, instr in self.__instructions:
            if (instr == "NOP1"):
                print(";", label, "instructions")
            s = f'\t\t{instr}' if label == None else f'{str(label+":"):<9}\t{instr}'
            print(s)
