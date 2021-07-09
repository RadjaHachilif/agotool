import os, sys, subprocess 
from shlex import split
import gzip
import pandas as pd
import numpy as np
import pickle
from collections import defaultdict
from collections import deque
# sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.realpath(__file__))))
from ast import literal_eval
import re, ast, obo_parser
import query, tools, ratio
import variables as variables
import datetime
import math

TYPEDEF_TAG, TERM_TAG = "[Typedef]", "[Term]"
BASH_LOCATION = r"/usr/bin/env bash"
PYTHON_DIR = variables.PYTHON_DIR
LOG_DIRECTORY = variables.LOG_DIRECTORY
POSTGRESQL_DIR = variables.POSTGRESQL_DIR
DOWNLOADS_DIR = variables.DOWNLOADS_DIR
STATIC_DIR = variables.STATIC_POSTGRES_DIR
TABLES_DIR = variables.TABLES_DIR
TEST_DIR = variables.TEST_DIR
FILES_NOT_2_DELETE = variables.FILES_NOT_2_DELETE
NUMBER_OF_PROCESSES = variables.NUMBER_OF_PROCESSES
VERSION_ = variables.VERSION_
PLATFORM = sys.platform

def _helper_get_taxid_2_total_protein_count_dict(fn_in_Taxid_2_Proteins_table_STRING):
    taxid_2_total_protein_count_dict = {}
    with open(fn_in_Taxid_2_Proteins_table_STRING, "r") as fh_in:
        for line in fh_in:
            # taxid, ENSP_arr_str, count = line.split("\t")
            taxid, count, ENSP_arr_str = line.split("\t")
            count = len(count.split(","))
            taxid_2_total_protein_count_dict[taxid] = str(count) # count is a String not an Int (since needs to be written to file)
    return taxid_2_total_protein_count_dict

def _helper_get_function_2_funcEnum_dict__and__function_2_etype_dict(fn_in_Functions_table):
    function_2_funcEnum_dict, function_2_etype_dict = {}, {}
    with open(fn_in_Functions_table, "r") as fh_in:
        for line in fh_in:
            #print(line)
            etype, an, description, year, hier_nr = line.split("\t")
            #function_2_funcEnum_dict[an] = enum
            function_2_etype_dict[an] = etype
    return function_2_funcEnum_dict, function_2_etype_dict

def _helper_parse_line_prot_2_func(line):
    taxid_ENSP, function_an_set_str, etype = line.split("\t")
    taxid = taxid_ENSP.split(".")[0]
    etype = etype.strip()
    function_an_set = set(function_an_set_str.split(","))
    return taxid_ENSP, taxid, etype, function_an_set

def Function_2_ENSP_table(fn_in_Protein_2_Function_table, fn_in_Taxid_2_Proteins_table, fn_in_Functions_table,
        fn_out_Function_2_ENSP_table_all, fn_out_Function_2_ENSP_table_reduced, fn_out_Function_2_ENSP_table_removed,
        min_count=1, verbose=True):

    """
    min_count: for each function minimum number of ENSPs per TaxID, e.g. 1 otherwise removed, also from Protein_2_Function_table_STRING
    """
    if verbose:
        print("creating Function_2_ENSP_table this will take a while")

    function_2_ENSPs_dict = defaultdict(list)
    taxid_2_total_protein_count_dict = _helper_get_taxid_2_total_protein_count_dict(fn_in_Taxid_2_Proteins_table)
    
    _, function_2_etype_dict = _helper_get_function_2_funcEnum_dict__and__function_2_etype_dict(fn_in_Functions_table) # funcenum not correct at this stage since some functions will be removed from Functions_table_STRING and thus the enumeration would be wrong
    with open(fn_in_Protein_2_Function_table, "r") as fh_in:
        taxid_ENSP, taxid_last, etype_dont_use, function_an_set = _helper_parse_line_prot_2_func(fh_in.readline())
        fh_in.seek(0)
        with open(fn_out_Function_2_ENSP_table_all, "w") as fh_out:
            #with open(fn_out_Function_2_ENSP_table_reduced, "w") as fh_out_reduced:
                #with open(fn_out_Function_2_ENSP_table_removed, "w") as fh_out_removed:
                    for line in fh_in:
                        taxid_ENSP, taxid, etype_dont_use, function_an_set = _helper_parse_line_prot_2_func(line)
                        if not taxid in taxid_2_total_protein_count_dict.keys():
                            continue
                        if taxid != taxid_last:
                            #if taxid_last == "9606":
                                #print("seen")
                                #print(function_2_ENSPs_dict)
                            num_ENSPs_total_for_taxid = taxid_2_total_protein_count_dict[taxid_last]
                            for function_an in function_2_ENSPs_dict.keys():
                                ENSPs = function_2_ENSPs_dict[function_an]
                                num_ENSPs = len(ENSPs)
                                # arr_of_ENSPs = format_list_of_string_2_postgres_array(ENSPs)
                                arr_of_ENSPs = ",".join(sorted(set(ENSPs)))
                                try:
                                    etype = function_2_etype_dict[function_an]
                                except KeyError: # for blacklisted terms in variables.py
                                    etype = "-1"
                                    #if "109582" in function_an and "HSA" in function_an:
                                    #print("function_an : ",function_an,"\n\n\n", "function_2_etype_dict:", function_2_etype_dict)

                                fh_out.write(taxid_last + "\t" + etype + "\t" + function_an + "\t" + str(num_ENSPs) + "\t" + num_ENSPs_total_for_taxid + "\t" + arr_of_ENSPs + "\n")
                                if num_ENSPs > min_count:
                                    fh_out_reduced.write(taxid_last + "\t" + etype + "\t" + function_an + "\t" + str(num_ENSPs) + "\t" + num_ENSPs_total_for_taxid + "\t" + arr_of_ENSPs + "\n")
                                else:
                                    fh_out_removed.write(taxid_last + "\t" + etype + "\t" + function_an + "\t" + str(num_ENSPs) + "\t" + num_ENSPs_total_for_taxid + "\t" + arr_of_ENSPs + "\n")
                            
                            function_2_ENSPs_dict = defaultdict(list)
                        else:
                            for function in function_an_set:
                                function_2_ENSPs_dict[function].append(taxid_ENSP)
                        taxid_last = taxid

                    num_ENSPs_total_for_taxid = taxid_2_total_protein_count_dict[taxid]
                    for function_an, ENSPs in function_2_ENSPs_dict.items():
                        num_ENSPs = len(ENSPs)
                        # arr_of_ENSPs = format_list_of_string_2_postgres_array(ENSPs)
                        arr_of_ENSPs = ",".join(sorted(set(ENSPs)))
                        try:
                            etype = function_2_etype_dict[function_an]
                        except KeyError:  # for blacklisted terms in variables.py
                            etype = "-1"
                        fh_out.write(taxid_last + "\t" + etype + "\t" + function_an + "\t" + str(num_ENSPs) + "\t" + num_ENSPs_total_for_taxid + "\t" + arr_of_ENSPs + "\n")
                        if num_ENSPs > min_count:
                            fh_out_reduced.write(taxid_last + "\t" + etype + "\t" + function_an + "\t" + str(num_ENSPs) + "\t" + num_ENSPs_total_for_taxid + "\t" + arr_of_ENSPs + "\n")
                        else:
                            fh_out_removed.write(taxid_last + "\t" + etype + "\t" + function_an + "\t" + str(num_ENSPs) + "\t" + num_ENSPs_total_for_taxid + "\t" + arr_of_ENSPs + "\n")
    tools.sort_file(fn_out_Function_2_ENSP_table_reduced, fn_out_Function_2_ENSP_table_reduced)
    if verbose:
        print("finished creating \n{}\nand\n{}".format(fn_out_Function_2_ENSP_table_all, fn_out_Function_2_ENSP_table_reduced))

tools.sort_file(TABLES_DIR+"/Functions_table_RCTM.txt", TABLES_DIR+"/Functions_table_RCTM.txt", number_of_processes=10, verbose=True)
tools.sort_file(TABLES_DIR+"/Protein_2_Function_table_RCTM.txt", TABLES_DIR+"/Protein_2_Function_table_RCTM.txt", number_of_processes=10, verbose=True)

Function_2_ENSP_table(TABLES_DIR+"/Protein_2_Function_table_STRING_all_but_PMID.txt", TABLES_DIR+"/Taxid_2_Proteins_table_STRING.txt", TABLES_DIR+"/Functions_table_STRING_all_but_PMID.txt_temp", "out_Function_2_ENSP_table_all.txt", "out_Function_2_ENSP_table_reduced.txt", "out_Function_2_ENSP_table_removed.txt", min_count=1, verbose=True)








