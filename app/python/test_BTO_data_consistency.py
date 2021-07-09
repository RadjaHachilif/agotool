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
import create_SQL_tables_snakemake as cst
import query, tools, ratio
import variables as variables
import datetime
import math


DOWNLOADS_DIR = variables.DOWNLOADS_DIR_SNAKEMAKE
TABLES_DIR = variables.TABLES_DIR_SNAKEMAKE
PYTHON_DIR = variables.PYTHON_DIR
NUMBER_OF_PROCESSES = variables.NUMBER_OF_PROCESSES
if NUMBER_OF_PROCESSES > 10:
    NUMBER_OF_PROCESSES_sorting = 10
else:
    NUMBER_OF_PROCESSES_sorting = NUMBER_OF_PROCESSES
verbose = variables.VERBOSE
TABLES_DICT_SNAKEMAKE = variables.TABLES_DICT_SNAKEMAKE
log_snakemake = os.path.join(variables.LOG_DIRECTORY, "log_snakemake.log")

# DOID_BTO_GOCC
Function_2_Description_DOID_BTO_GO_down = os.path.join(DOWNLOADS_DIR, "Function_2_Description_DOID_BTO_GO.txt.gz")
Functions_table_DOID_BTO_GOCC = os.path.join( "Functions_table_DOID_BTO_GOCC_test.txt")
BTO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "bto_Jensenlab.obo") # static file
DOID_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "doid_Jensenlab.obo")
GO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "go_Jensenlab.obo")
Blacklisted_terms_Jensenlab = os.path.join(DOWNLOADS_DIR, "blacklisted_terms_Jensenlab.txt")

# Functions_table_DOID_BTO_GOCC # these are not being filtered to relevant ones, but since number is small (~20k), the impact should be negligible
GO_CC_textmining_additional_etype = True

cst.Functions_table_DOID_BTO_GOCC(Function_2_Description_DOID_BTO_GO_down, BTO_obo_Jensenlab, DOID_obo_Jensenlab, GO_obo_Jensenlab, Blacklisted_terms_Jensenlab, Functions_table_DOID_BTO_GOCC, GO_CC_textmining_additional_etype, NUMBER_OF_PROCESSES_sorting, verbose=True)
