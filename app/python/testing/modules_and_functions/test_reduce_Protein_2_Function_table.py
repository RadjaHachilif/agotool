import create_SQL_tables_snakemake as cst
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "python"))
import variables
TABLES_DIR = variables.TABLES_DIR_SNAKEMAKE
PYTHON_DIR = variables.PYTHON_DIR

Protein_2_Function_table_STRING_all = os.path.join(TABLES_DIR, "Protein_2_Function_table_STRING_all.txt")
Function_2_ENSP_table_STRING_removed = os.path.join(TABLES_DIR, "Function_2_ENSP_table_STRING_removed.txt")
Functions_table_STRING_reduced = os.path.join(TABLES_DIR, "Functions_table_STS_FIN.txt")
Protein_2_Function_table_STRING_reduced = os.path.join(TABLES_DIR, "Protein_2_Function_table_STRING.txt")
Protein_2_Function_table_STRING_removed = os.path.join(TABLES_DIR, "Protein_2_Function_table_STRING_removed.txt")

cst.reduce_Protein_2_Function_table(Protein_2_Function_table_STRING_all, Function_2_ENSP_table_STRING_removed, Functions_table_STRING_reduced, Protein_2_Function_table_STRING_reduced, Protein_2_Function_table_STRING_removed)

