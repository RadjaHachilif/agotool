import create_SQL_tables_snakemake as cst
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "python"))
import variables
TABLES_DIR = variables.TABLES_DIR_SNAKEMAKE
PYTHON_DIR = variables.PYTHON_DIR

Taxid_2_Proteins_table_STRING = os.path.join(TABLES_DIR, "Taxid_2_Proteins_table_STS_FIN.txt")
fn_out_Protein_2_Function_table_STRING = os.path.join(TABLES_DIR, "Protein_2_Function_table_STRING_all.txt")
fn_out_Protein_2_Function_table_STRING_temp = fn_out_Protein_2_Function_table_STRING + "_temp"
fn_out_Protein_2_Function_table_STRING_rest = fn_out_Protein_2_Function_table_STRING + "_rest" 

cst.reduce_Protein_2_Function_table_2_STRING_proteins(fn_out_Protein_2_Function_table_STRING_temp, Taxid_2_Proteins_table_STRING, fn_out_Protein_2_Function_table_STRING, fn_out_Protein_2_Function_table_STRING_rest, number_of_processes=20)


