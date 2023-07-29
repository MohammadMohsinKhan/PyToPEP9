import random
import string

class SymbolTable:
    def __init__(self, extractorResults, top_level, localVars, functionInstructions):
        self.extractorResults = extractorResults
        self.top_level = top_level
        self.localVars = localVars
        self.functionInstructions = functionInstructions
        self.changedGlobalVars = {}
        self.renameGlobalVars()
        self.knownVarNames = self.shortenVarName(self.extractorResults)[1]
        self.changedVarNames = self.shortenVarName(self.extractorResults)[0]
        self.NewMainInstructionNames = self.changeInstrunctionNames(self.top_level, self.knownVarNames)
        self.localKnownVarNames = self.shortenLocalVarName(self.localVars)[1]
        self.localChangedVarNames = self.shortenLocalVarName(self.localVars)[0]
        self.NewLocalInstructionNames = self.changeLocalInstrunctionNames(self.functionInstructions, self.localKnownVarNames)

    # Checks if a global variable is a local variable as well and renames it
    def renameGlobalVars(self):
        for var in list(self.extractorResults):
            if isinstance(var, tuple):
                if var[0] in self.localVars:
                    newName = ''.join(random.sample(string.ascii_uppercase, 6)).lower()
                    self.changedGlobalVars[var[0]] = newName
                    self.extractorResults.remove(var)
                    self.extractorResults.add(newName, var[1])
            else:
                if var in self.localVars:
                    newName = ''.join(random.sample(string.ascii_uppercase, 6)).lower()
                    self.changedGlobalVars[var] = newName
                    self.extractorResults.remove(var)
                    self.extractorResults.add(newName)

    # if a variable name was changed, change it in the instructions as well for global variables
    def changeInstrunctionNames(self, oldInstructionNames, changedVarNames):
        NewInstructionNames = []

        for intsruction in oldInstructionNames:
            in_instr = False
            if ("," in intsruction[1]):
                varname = intsruction[1].split(",")[0].split(" ")[1]
                in_instr = True

            if in_instr and varname in changedVarNames:
                NewInstructionNames.append((intsruction[0], intsruction[1].replace(varname, changedVarNames[varname])))
            else: NewInstructionNames.append(intsruction)

        return NewInstructionNames
    
    # If a global variable is too long, shorten it
    def shortenVarName(self, results):
        changedVarNames = set()
        knownVarNames = {}
        counter = 0

        for result in results:
            var = result
            res = None

            if self.is_tuple(var):
                var = result[0]
                if len(result) == 3: res = result[2]

            if (len(var) > 8):
                if var not in knownVarNames:
                    knownVarNames[var] = var[:8 - len(str(counter))] + str(counter)
                if self.is_tuple(var): changedVarNames.add((knownVarNames[var], result[1], res))
                else: changedVarNames.add(knownVarNames[var])
                
            else:
                if self.is_tuple(result): changedVarNames.add((var, result[1], res))
                else: changedVarNames.add(var)

        return changedVarNames, knownVarNames

    # If a local variable is too long, shorten it
    def shortenLocalVarName(self, results):
        changedVarNames = {}
        knownVarNames = {}
        counter = 0

        for result in results:
            var = result
            if (len(result) > 8):
                if result not in knownVarNames:
                    knownVarNames[result] = result[:8 - len(str(counter))] + str(counter)
                    var = knownVarNames[result]
            changedVarNames[var] = results[result]

        return changedVarNames, knownVarNames
    
    # if a variable name was changed, change it in the instructions as well for local variables
    def changeLocalInstrunctionNames(self, oldInstructionNames, changedVarNames):
        NewInstructionNames = []

        for intsruction in oldInstructionNames:
            in_instr = False
            if ("," in intsruction[1]):
                varname = intsruction[1].split(",")[0].split(" ")[1]
                in_instr = True

            if in_instr and varname in changedVarNames:
                replaced_instr = intsruction[1].replace(varname, changedVarNames[varname])
                NewInstructionNames.append((intsruction[0], replaced_instr))
            else:
                NewInstructionNames.append(intsruction)

        return NewInstructionNames

    # Getters
    def getNewMainInstructionNames(self):
        return self.NewMainInstructionNames
    
    def getChangedVarNames(self):
        return self.changedVarNames
    
    def getKnownVarNames(self):
        return self.knownVarNames

    def getNewLocalInstructionNames(self):
        return self.NewLocalInstructionNames

    def getLocalChangedVarNames(self):
        return self.localChangedVarNames

    def getLocalKnownVarNames(self):
        return self.localKnownVarNames
    
    def getChangedGlobalVars(self):
        return self.changedGlobalVars
    
    # Checks if a variable is a tuple
    def is_tuple(self, var):
        return isinstance(var, tuple)
