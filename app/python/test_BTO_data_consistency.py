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


# DOID_BTO_GOCC
Function_2_Description_DOID_BTO_GO_down = os.path.join(DOWNLOADS_DIR, "Function_2_Description_DOID_BTO_GO.txt.gz")
Functions_table_DOID_BTO_GOCC = os.path.join(TABLES_DIR, "Functions_table_DOID_BTO_GOCC.txt")
BTO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "bto_Jensenlab.obo") # static file

# Functions_table_DOID_BTO_GOCC # these are not being filtered to relevant ones, but since number is small (~20k), the impact should be negligible
GO_CC_textmining_additional_etype = True

cst.Functions_table_DOID_BTO_GOCC(Function_2_Description_DOID_BTO_GO_down, BTO_obo_Jensenlab, DOID_obo_Jensenlab, GO_obo_Jensenlab, Blacklisted_terms_Jensenlab, Functions_table_DOID_BTO_GOCC, GO_CC_textmining_additional_etype, threads = NUMBER_OF_PROCESSES_sorting, verbose)
