import argparse
import ast
from visitors.GlobalVariables import GlobalVariableExtraction
from visitors.TopLevelProgram import TopLevelProgram
from generators.StaticMemoryAllocation import StaticMemoryAllocation
from generators.DynamicMemoryAllocation import DynamicMemoryAllocation
from generators.EntryPoint import EntryPoint
from SymbolTable.SymbolTable import SymbolTable
from visitors.LocalVariables import LocalVariableExtraction
import copy

def main():
    input_file, print_ast = process_cli()
    with open(input_file) as f:
        source = f.read()
    node = ast.parse(source)
    if print_ast:
        print(ast.dump(node, indent=2))
    else:
        process(input_file, node)
    
def process_cli():
    """"Process Command Line Interface options"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='filename to compile (.py)')
    parser.add_argument('--ast-only', default=False, action='store_true')
    args = vars(parser.parse_args())
    return args['f'], args['ast_only']

def is_func(node): 
    return isinstance(node, ast.FunctionDef)

# function used to create an ast with only function definitions
def get_func_data(temp):
    while True:
        body, flag = temp.body, False
        for node in body:
            if not is_func(node):
                body.remove(node)
        
        for node in body:
            if not is_func(node): flag = True
        if not flag: break
    
    for node in body:
        if is_func(node): return temp
            
    return None

def process(input_file, root_node):
    print(f'; Translating {input_file}')
    extractor = GlobalVariableExtraction()
    extractor.visit(root_node)
    LocalExtractor = LocalVariableExtraction()
    top_level = TopLevelProgram('tl')
    top_level.visit(root_node)
    temp = get_func_data(root_node)
    if temp: LocalExtractor.visit(temp)
    symbolTable = SymbolTable(extractor.results, top_level.finalize(), LocalExtractor.getLocalVars(), LocalExtractor.finalize())
    memory_alloc = StaticMemoryAllocation(symbolTable.getChangedVarNames(), symbolTable.getChangedGlobalVars())
    LocalMemoryAlloc = DynamicMemoryAllocation(symbolTable.getLocalChangedVarNames())
    print('; Branching to top level (tl) instructions')
    print('\t\tBR tl')
    memory_alloc.generate()
    LocalMemoryAlloc.generate()
    ep = EntryPoint(symbolTable.getNewMainInstructionNames(), symbolTable.getChangedGlobalVars())
    if temp:
        ep2 = EntryPoint(symbolTable.getNewLocalInstructionNames(), {}, True)
        ep2.generate()
    ep.generate()


    
if __name__ == '__main__':
    main()
