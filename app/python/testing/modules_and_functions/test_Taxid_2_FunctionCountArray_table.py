import create_SQL_tables_snakemake as cst
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "python"))
import variables
TABLES_DIR = variables.TABLES_DIR_SNAKEMAKE
PYTHON_DIR = variables.PYTHON_DIR

Protein_2_FunctionEnum_table_STRING = os.path.join(TABLES_DIR, "Protein_2_FunctionEnum_table_STS_FIN.txt")
Functions_table_STRING = os.path.join(TABLES_DIR, "Functions_table_STS_FIN.txt")
Taxid_2_FunctionCountArray_table_STRING = os.path.join(TABLES_DIR, "Taxid_2_FunctionCountArray_table_STS_FIN.txt")
Taxid_2_Proteins_table_STRING = os.path.join(TABLES_DIR, "Taxid_2_Proteins_table_STS_FIN.txt")

cst.Taxid_2_FunctionCountArray_table_STRING(Protein_2_FunctionEnum_table_STRING, Functions_table_STRING, Taxid_2_Proteins_table_STRING, Taxid_2_FunctionCountArray_table_STRING, number_of_processes=30)

