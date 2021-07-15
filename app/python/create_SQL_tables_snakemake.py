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

def Protein_2_Function_table_InterPro(fn_in_string2interpro, fn_in_Functions_table_InterPro, fn_in_interpro_parent_2_child_tree, fn_out_Protein_2_Function_table_InterPro, number_of_processes=1, verbose=True):
    """
    :param fn_in_string2interpro: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/downloads/string2interpro.dat.gz)
    :param fn_out_Protein_2_Function_table_InterPro: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/Protein_2_Function_table_InterPro.txt)
    :param fn_in_interpro_parent_2_child_tree: String (download from interpro downloads page)
    :param fn_in_Functions_table_InterPro: String (/home/dblyon/agotool/data/PostgreSQL/tables/Functions_table_InterPro.txt) with InterPro ANs to verify
    :param number_of_processes: Integer (number of cores, shouldn't be too high since Disks are probably the bottleneck even with SSD, e.g. max 4)
    :param verbose: Bool (flag to print infos)
    :return: None
    """
    ### sort by fn_in first column (data is most probably already sorted, but we need to be certain for the parser that follows)
    ### unzip first, then sort to enable parallel sorting
    ### is the output is NOT zipped, but the
    ### e.g. of line "1298865.H978DRAFT_0001  A0A010P2C8      IPR011990       Tetratricopeptide-like helical domain superfamily       G3DSA:1.25.40.10        182     292"
    if verbose:
        print("\ncreate_Protein_2_Function_table_InterPro")
    fn_in_temp = fn_in_string2interpro + "_temp"
    tools.gunzip_file(fn_in_string2interpro, fn_in_temp)
    tools.sort_file(fn_in_temp, fn_in_temp, columns="1", number_of_processes=number_of_processes, verbose=verbose)
    child_2_parent_dict, _ = get_child_2_direct_parents_and_term_2_level_dict_interpro(fn_in_interpro_parent_2_child_tree)
    lineage_dict = get_lineage_from_child_2_direct_parent_dict(child_2_parent_dict)
    df = pd.read_csv(fn_in_Functions_table_InterPro, sep='\t', names=["etype", "AN", "description", "year", "level"])
    InterPro_AN_superset = set(df["AN"].values.tolist())
    if verbose:
        print("parsing previous result to produce Protein_2_Function_table_InterPro.txt")
    entityType_InterPro = variables.id_2_entityTypeNumber_dict["INTERPRO"]
    with open(fn_out_Protein_2_Function_table_InterPro, "w") as fh_out:
        for ENSP, InterProID_list in parse_string2interpro_yield_entry(fn_in_temp):
            # InterProID_list = sorted({id_ for id_ in InterProID_list if id_ in InterPro_AN_superset})
            # backtrack functions
            InterProID_set = set(InterProID_list)
            for id_ in InterProID_list:
                InterProID_set.update(lineage_dict[id_])
            InterProID_list = sorted(InterProID_set.intersection(InterPro_AN_superset))
            if len(InterProID_list) >= 1:
                fh_out.write(ENSP + "\t" + format_list_of_string_2_postgres_array(InterProID_list) + "\t" + entityType_InterPro + "\n")
    os.remove(fn_in_temp)
    if verbose:
        print("done create_Protein_2_Function_table_InterPro\n")

def parse_string2interpro_yield_entry(fn_in):
    # "1298865.H978DRAFT_0001  A0A010P2C8      IPR011990       Tetratricopeptide-like helical domain superfamily       G3DSA:1.25.40.10        182     292"
    InterProID_list = []
    did_first = False
    for line in tools.yield_line_uncompressed_or_gz_file(fn_in):
        ENSP, UniProtAN, InterProID, *rest = line.split()
        if not did_first:
            ENSP_previous = ENSP
            did_first = True
        if ENSP == ENSP_previous:
            InterProID_list.append(InterProID)
        else:
            yield (ENSP_previous, InterProID_list)
            InterProID_list = [InterProID]
            ENSP_previous = ENSP
    yield (ENSP_previous, InterProID_list)

def create_protein_2_function_table_Reactome(fn_in, fn_out, child_2_parent_dict, return_all_terms=False):  # term_set_2_use_as_filter
    # entity_type = "-57"
    entity_type = variables.id_2_entityTypeNumber_dict["Reactome"]
    if return_all_terms:
        all_terms = set()
    with open(fn_in, "r") as fh_in:
        with open(fn_out, "w") as fh_out:
            line = fh_in.readline()
            taxid, ENSP_without_taxid, term = line.split("\t")
            ENSP = "{}.{}".format(taxid, ENSP_without_taxid)
            term = term.strip()
            term_list = [term] + list(get_parents_iterative(term, child_2_parent_dict))
            if return_all_terms:
                all_terms = all_terms.union(set(term_list))
            ENSP_last = ENSP
            for line in fh_in:
                taxid, ENSP_without_taxid, term = line.split("\t")
                ENSP = "{}.{}".format(taxid, ENSP_without_taxid)
                term = term.strip()
                if ENSP == ENSP_last:
                    term_list += [term] + list(get_parents_iterative(term, child_2_parent_dict))
                    if return_all_terms:
                        all_terms = all_terms.union(set(term_list))
                else:
                    term_string_array = "{" + str(sorted(set(term_list)))[1:-1].replace("'", '"') + "}"
                    fh_out.write(ENSP_last + "\t" + term_string_array + "\t" + entity_type + "\n")
                    term_list = [term] + list(get_parents_iterative(term, child_2_parent_dict))
                    if return_all_terms:
                        all_terms = all_terms.union(set(term_list))
                ENSP_last = ENSP
            term_string_array = "{" + str(sorted(set(term_list)))[1:-1].replace("'", '"') + "}"
            fh_out.write(ENSP_last + "\t" + term_string_array + "\t" + entity_type + "\n")
            term_list = [term] + list(get_parents_iterative(term, child_2_parent_dict))
            if return_all_terms:
                all_terms = all_terms.union(set(term_list))
                return all_terms

def create_Functions_table_Reactome(fn_in, fn_out, term_2_level_dict, all_terms):
    """
    :param fn_in: String (RCTM_associations_sorted.txt)
    :param fn_out: String (Function_table_RCTM.txt)
    :param term_2_level_dict: Dict(key: RCTM-term, val: hierarchical level)
    :param all_terms: Set of String (with all RCTM terms that have any association with the given ENSPs)
    :return: Tuple (List of terms with hierarchy, Set of terms without hierarchy)
    do a sanity check: are terms without a hierarchy used in protein_2_function
    create file Functions_table_Reactome.txt
    etype, term, name, definition, description # old
    | enum | etype | an | description | year | level | # new
    """
    # entity_type = "-57"
    entity_type = variables.id_2_entityTypeNumber_dict["Reactome"]
    year = "-1"
    terms_with_hierarchy, terms_without_hierarchy = [], []
    with open(fn_in, "r") as fh_in:
        with open(fn_out, "w") as fh_out:
            for line in fh_in:
                term, url_, description = line.split("\t")
                if term.startswith("R-"):  # R-ATH-109581 --> ATH-109581
                    term = term[2:]
                description = description.strip()
                try:
                    level = term_2_level_dict[term]
                    terms_with_hierarchy.append(term)
                except KeyError:
                    terms_without_hierarchy.append(term)
                    level = "-1"
                if term in all_terms:  # filter relevant terms that occur in protein_2_functions_tables_RCTM.txt
                    fh_out.write(entity_type + "\t" + term + "\t" + description + "\t" + year + "\t" + str(level) + "\n")
    return sorted(set(terms_with_hierarchy)), sorted(set(terms_without_hierarchy))

def get_direct_parents(child, child_2_parent_dict):
    try:
        # copy is necessary since child_2_parent_dict is otherwise modified by updating direct_parents in get_all_lineages
        # direct_parents = child_2_parent_dict[child].copy() # deprecated
        direct_parents = child_2_parent_dict[child]
    except KeyError:
        direct_parents = []
    return direct_parents

def get_parents_iterative(child, child_2_parent_dict):
    """
    par = {"C22":{"C1"}, "C21":{"C1"}, "C1":{"P1"}}
    get_parents_iterative("C22", par)
    """
    if child not in child_2_parent_dict:
        return []
    # important to set() otherwise parent is updated in orig object
    all_parents = set(child_2_parent_dict[child])
    current_parents = set(all_parents)
    while len(current_parents) > 0:
        new_parents = set()
        for parent in current_parents:
            if parent in child_2_parent_dict:
                temp_parents = child_2_parent_dict[parent].difference(all_parents)
                all_parents.update(temp_parents)
                new_parents.update(temp_parents)
        current_parents = new_parents
    return all_parents

def get_term_2_level_dict(child_2_parent_dict):
    """
    direct parents
    calculate level of hierarchy for data
    if term in hierarchy --> default to level 1
    if term not in hierarchy --> not present in dict
    """
    term_2_level_dict = defaultdict(lambda: 1)
    for child in child_2_parent_dict.keys():
        lineages = get_all_lineages(child, child_2_parent_dict)
        try:
            level = len(max(lineages, key=len)) # if not in dict
        except ValueError: # if lineage [] but not [[]], which can happen for top root terms
            level = 1
        if level == 0: # for root terms
            level = 1
        term_2_level_dict[child] = level
    return term_2_level_dict

def get_child_2_direct_parent_dict_from_dag(dag):
    """
    e.g. {'GO:1901681': {'GO:0005488'},
    'GO:0090314': {'GO:0090313', 'GO:0090316', 'GO:1905477'}, ...}
    """
    child_2_direct_parents_dict = {}
    for name, term_object in dag.items():
        child_2_direct_parents_dict[name] = {p.id for p in term_object.parents}
    return child_2_direct_parents_dict

def get_all_lineages(child, child_2_parent_dict):
    """
    previous recursive version below
    def extend_parents(child_2_parent_dict, lineages=[]):
        for lineage in lineages:
            parents = list(get_direct_parents(lineage[-1], child_2_parent_dict))
            len_parents = len(parents)
            if len_parents == 1: # if single direct parents recursively walk up the tree
                lineage.extend(parents)
                return extend_parents(child_2_parent_dict, lineages)
            elif len_parents > 1: # multiple direct parents
                lineage_temp = lineage[:]
                lineage.extend([parents[0]]) # extend first parent
                for parent in parents[1:]: # copy lineage for the other parents and extend with respective parent
                    lineages.append(lineage_temp + [parent])
                return extend_parents(child_2_parent_dict, lineages)
        return lineages

    def get_all_lineages(child, child_2_parent_dict):
        lineages = []
        for parent in get_direct_parents(child, child_2_parent_dict):
            lineages += extend_parents(child_2_parent_dict, [[child, parent]])
        return lineages
    """
    lineage = [child]
    lineages = [lineage]
    visit_plan = deque()
    visit_plan.append((child, lineage))
    while visit_plan:
        (next_to_visit, lineage) = visit_plan.pop() # # lineage = # for this next_to_visit dude
        parents = list(get_direct_parents(next_to_visit, child_2_parent_dict))
        len_parents = len(parents)
        if len_parents == 1:  # if single direct parents recursively walk up the tree
            lineage.append(parents[0])
            visit_plan.append((parents[0], lineage))
        elif len_parents > 1:  # multiple direct parents
            # remove original/old lineage and replace with the forked
            lineages.remove(lineage)
            for parent in parents:  # copy lineage for the other parents and extend with respective parent
                lineage_fork = lineage[:]
                lineage_fork.append(parent)
                lineages.append(lineage_fork)
                visit_plan.append((parent, lineage_fork))
    return lineages

def Protein_2_Function_table_RCTM__and__Function_table_RCTM(fn_associations, fn_descriptions, fn_hierarchy, fn_protein_2_function_table_RCTM, fn_functions_table_RCTM, number_of_processes):
    """
    fn_associations=snakemake.input[0],
    fn_descriptions=snakemake.input[1],
    fn_hierarchy=snakemake.input[2],
    fn_protein_2_function_table_RCTM=snakemake.output[0],
    fn_functions_table_RCTM=snakemake.output[1],
    number_of_processes=snakemake.config["number_of_processes"]
    """
    if variables.VERBOSE:
        print("### creating 2 tables:\n - Protein_2_Function_table_RCTM.txt\n - Function_table_RCTM.txt\n")
    # sort on first two columns in order to get all functional associations for a given ENSP in one block
    tools.sort_file(fn_associations, fn_associations, number_of_processes=number_of_processes, verbose=variables.VERBOSE)
    child_2_parent_dict = get_child_2_direct_parent_dict_RCTM(fn_hierarchy)  # child_2_parent_dict --> child 2 direct parents
    term_2_level_dict = get_term_2_level_dict(child_2_parent_dict)
    all_terms = create_protein_2_function_table_Reactome(fn_in=fn_associations, fn_out=fn_protein_2_function_table_RCTM, child_2_parent_dict=child_2_parent_dict, return_all_terms=True)
    terms_with_hierarchy, terms_without_hierarchy = create_Functions_table_Reactome(fn_in=fn_descriptions, fn_out=fn_functions_table_RCTM, term_2_level_dict=term_2_level_dict, all_terms=all_terms)
    if variables.VERBOSE:
        print("number of terms_without_hierarchy", len(terms_without_hierarchy))
        print("## done with RCTM tables")

def string_2_interpro(fn_in_string2uniprot, fn_in_uniprot2interpro, fn_out_string2interpro):
    """
    fn_in_string2uniprot=snakemake.input[0],
    fn_in_uniprot2interpro=snakemake.input[1],
    fn_out_string2interpro=snakemake.output[0]
    read string to uniprot mapping and reverse
    input line e.g. 742765.HMPREF9457_01522 [TAB] G1WQX1
    """
    uniprot2string = {}
    # with gzip.open(input.string2uniprot,'rt') as f:
    with open(fn_in_string2uniprot, 'r') as fh_string2uniprot:
        for line in fh_string2uniprot:
            if line.startswith('#'):
                continue
            # string_id, uniprot_ac = line.rstrip().split('\t')
            split_ = line.strip().split()
            uniprot_ac = split_[1].split("|")[0]
            string_id = split_[2]
            uniprot2string[uniprot_ac] = string_id

    # read uniprot to interpro mapping and map to string (one to many, i.e. string_id:list_interpro_entries)
    # input line e.g.  G1WQX1 [TAB] IPR021778 [TAB] Domain of unknown function DUF3343 [TAB] PF11823 [TAB] 8 [TAB] 68
    string2interpro = {}
    with gzip.open(fn_in_uniprot2interpro, 'rt') as fh_in: # read binary file
        for line in fh_in:
            l = line.split('\t')
            uniprot_ac = l[0]
            if uniprot_ac in uniprot2string:
                string_id = uniprot2string[uniprot_ac]
                if string_id not in string2interpro:
                    string2interpro[string_id] = []
                string2interpro[string_id].append(line)

    # write out string2interpro mapping
    # output line e.g. 742765.HMPREF9457_01522 [TAB] G1WQX1 [TAB] IPR021778 [TAB] Domain of unknown function DUF3343 [TAB] PF11823 [TAB] 8 [TAB] 68
    with gzip.open(fn_out_string2interpro, 'wt') as fh_out:
    # with open(fn_out_string2interpro, 'w') as fh_out:  # gzip.open
        for string_id in string2interpro:
            for line in string2interpro[string_id]:
                # fh_out.write('%s\t%s'%(string_id, line))
                fh_out.write("{}\t{}".format(string_id, line))

def Functions_table_InterPro(fn_in_interprot_AN_2_name, fn_in_interpro_parent_2_child_tree, fn_out_Functions_table_InterPro):
    """
    # | enum | etype | an | description | year | level |
    ### old file called InterPro_name_2_AN.txt
    # ftp://ftp.ebi.ac.uk/pub/databases/interpro/names.dat
    # df = pd.read_csv(fn_in, sep='\t', names=["an", "description"])
    # df["etype"] = variables.id_2_entityTypeNumber_dict["INTERPRO"]
    # df["year"] = "-1"
    # df["level"] = "-1"
    # df = df[["etype", "an", "description", "year", "level"]]
    # df.to_csv(fn_out, sep="\t", header=False, index=False)
    """
    child_2_parent_dict, term_2_level_dict = get_child_2_direct_parents_and_term_2_level_dict_interpro(fn_in_interpro_parent_2_child_tree)
    df = pd.read_csv(fn_in_interprot_AN_2_name, sep='\t')
    df = df.rename(columns={"ENTRY_AC": "an", "ENTRY_NAME": "description"})
    df["year"] = "-1"
    df["etype"] = variables.id_2_entityTypeNumber_dict["INTERPRO"]
    df["level"] = df["an"].apply(lambda term: term_2_level_dict[term])
    df = df[["etype", "an", "description", "year", "level"]]
    df.to_csv(fn_out_Functions_table_InterPro, sep="\t", header=False, index=False)

def get_child_2_direct_parents_and_term_2_level_dict_interpro(fn):
    """
    thus far no term has multiple parents, but code should capture these cases as well if they appear in the future

    IPR041492::Haloacid dehalogenase-like hydrolase:: # term_previous=IPR041492, level_previous=0
    --IPR006439::HAD hydrolase, subfamily IA:: # term=IPR006439, level=1 | term_previous=IPR006439, level_previous=1
    ----IPR006323::Phosphonoacetaldehyde hydrolase:: # term=IPR006323, level=2 | term_previous=IPR006323, level_previous=2
    ----IPR006328::L-2-Haloacid dehalogenase:: # term=IPR006328, level=2
    ----IPR006346::2-phosphoglycolate phosphatase-like, prokaryotic::
    ------IPR037512::Phosphoglycolate phosphatase, prokaryotic::
    ----IPR006351::3-amino-5-hydroxybenzoic acid synthesis-related::
    ----IPR010237::Pyrimidine 5-nucleotidase::
    ----IPR010972::Beta-phosphoglucomutase::
    ----IPR011949::HAD-superfamily hydrolase, subfamily IA, REG-2-like::
    ----IPR011950::HAD-superfamily hydrolase, subfamily IA, CTE7::
    ----IPR011951::HAD-superfamily hydrolase, subfamily IA, YjjG/YfnB::
    ----IPR023733::Pyrophosphatase PpaX::
    ----IPR023943::Enolase-phosphatase E1::
    ------IPR027511::Enolase-phosphatase E1, eukaryotes::
    :param fn: string (interpro_parent_2_child_tree.txt)
    :return dict: key: string val: set of string
    """
    child_2_parent_dict = defaultdict(lambda: set())
    term_2_level_dict = defaultdict(lambda: 1)
    with open(fn, "r") as fh:
        for line in fh:
            if not line.startswith("-"):
                term_previous = line.split(":")[0]
                level_previous = 1
                term_2_level_dict[term_previous] = level_previous
            else:
                term = line.split(":")[0]
                index_ = term.rfind("-")
                level_string = term[:index_ + 1]
                term = term[index_ + 1:]
                level = int(len(level_string) / 2) + 1
                term_2_level_dict[term] = level
                if level > level_previous:
                    if term not in child_2_parent_dict:
                        child_2_parent_dict[term] = {term_previous}
                    else:
                        child_2_parent_dict[term].update({term_previous})
                elif level == level_previous:
                    if term not in child_2_parent_dict:
                        child_2_parent_dict[term] = child_2_parent_dict[term_previous]
                    else:
                        child_2_parent_dict[term].update({child_2_parent_dict[term_previous]})
                elif level < level_previous:
                    term_previous, level_previous = helper_get_previous_term_and_level(child_2_parent_dict, term_2_level_dict, term_previous, level)
                    if term not in child_2_parent_dict:
                        child_2_parent_dict[term] = {term_previous}
                    else:
                        child_2_parent_dict[term].update({term_previous})
                level_previous = level
                term_previous = term
    return child_2_parent_dict, term_2_level_dict

def helper_get_previous_term_and_level(child_2_parent_dict, term_2_level_dict, term_previous, level_current):
    while True:
        term_previous = next(iter(child_2_parent_dict[term_previous]))
        level_previous = term_2_level_dict[term_previous]
        if level_current > level_previous:
            return term_previous, level_previous

def Functions_table_KEGG(fn_in, fn_out, verbose=True):
    """
    # | enum | etype | an | description | year | level |
    """
    etype = variables.id_2_entityTypeNumber_dict["KEGG"]
    level = "-1"
    year = "-1"
    if verbose:
        print("creating {} ".format(fn_out))
    with open(fn_out, "w") as fh_out:
        with open(fn_in, "r") as fh_in:
            for line in fh_in:
                if line.startswith("#"):
                    continue
                an, description = line.strip().split("\t")
                an = "map" + an
                string_2_write = etype + "\t" + an + "\t" + description + "\t" + year +"\t" + level + "\n"
                fh_out.write(string_2_write)

def Functions_table_SMART(fn_in, fn_out_functions_table_SMART, max_len_description, fn_out_map_name_2_an_SMART):
    """
    # | enum | etype | an | description | year | level |
    """
    # http://smart.embl-heidelberg.de/smart/descriptions.pl downloaded 20180808
    columns = ['DOMAIN', 'ACC', 'DEFINITION', 'DESCRIPTION']
    df = pd.read_csv(fn_in, sep="\t", skiprows=2, names=columns)
    # "etype" --> -53
    # "name" --> "DOMAIN"
    # "an" --> "ACC"
    # "definition" --> "DEFINITION; DESCRIPTION"
    entityType_SMART = variables.id_2_entityTypeNumber_dict["SMART"]
    df["etype"] = entityType_SMART
    df = df[["etype", "DOMAIN", "ACC", "DEFINITION", "DESCRIPTION"]]
    df["definition"] = df["DEFINITION"].fillna("") + "; " + df["DESCRIPTION"].fillna("")
    df["definition"] = df["definition"].apply(lambda x: x.replace("\n", "").replace("\t", " "))
    df = df[["etype", "DOMAIN", "ACC", "definition"]]
    df = df.rename(index=str, columns={"DOMAIN": "name", "ACC": "an"})
    df["description"] = df[["name", "definition"]].apply(parse_SMART, axis=1, args=(max_len_description, ))
    df["year"] = "-1"
    df["level"] = "-1"
    df1 = df[["etype", "an", "description", "year", "level"]]
    df1.to_csv(fn_out_functions_table_SMART, sep="\t", header=False, index=False)
    df2 = df[["name", "an"]]
    df2.to_csv(fn_out_map_name_2_an_SMART, sep="\t", header=False, index=False)

def parse_SMART(s, max_len_description=80):
    name = s["name"].strip()
    definition = s["definition"].strip().split(";")
    if definition[0].strip():  # not empty string
        string_ = definition[0].strip()
    elif definition[1].strip():  # not empty string
        string_ = definition[1].strip()
    else:
        string_ = name
    string_ = cut_long_string_at_word(string_, max_len_description=max_len_description)
    return string_

def Functions_table_PFAM(fn_in, fn_out_functions_table_PFAM, fn_out_map_name_2_an):
    # ftp://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.clans.tsv.gz (from 24/02/2017 downloaded 20180808)
    # fn = r"/home/dblyon/agotool/data/PostgreSQL/downloads/Pfam-A.clans.tsv"
    # fn_out = r"/home/dblyon/agotool/data/PostgreSQL/tables/Functions_table_PFAM.txt"
    columns = ['an', 'clan_an', 'HOMSTRAD', 'name', 'description']
    df = pd.read_csv(fn_in, sep="\t", names=columns)
    df["etype"] = variables.id_2_entityTypeNumber_dict["PFAM"]
    df["year"] = "-1"
    df["level"] = "-1"
    df1 = df[["etype", "an", "description", "year", "level"]]
    df1.to_csv(fn_out_functions_table_PFAM, sep="\t", header=False, index=False)
    df2 = df[["name", "an"]]
    df2.to_csv(fn_out_map_name_2_an, sep="\t", header=False, index=False)

def Functions_table_GO_or_UPK(fn_in_go_basic, fn_out_functions, is_upk=False):
    """
    # fn_in_go_basic = os.path.join(DOWNLOADS_DIR, "go-basic.obo")
    # fn_out_funcs = os.path.join(TABLES_DIR, "Functions_table_GO.txt")
    # ### functions [Functions_table_STRING.txt]
    # | enum | etype | an | description | year | level |
    id_, name --> Functions_table.txt
    id_, is_a_list --> Child_2_Parent_table_GO.txt
    :return:
    """
    obo = obo_parser.OBOReader_2_text(fn_in_go_basic)
    GO_dag = obo_parser.GODag(obo_file=fn_in_go_basic, upk=is_upk)
    year = "-1"
    child_2_parent_dict = get_child_2_direct_parent_dict_from_dag(GO_dag) # obsolete or top level terms have empty set for parents
    term_2_level_dict = get_term_2_level_dict(child_2_parent_dict)
    with open(fn_out_functions, "w") as fh_funcs:
        for entry in obo:
            id_, name, is_a_list, definition = entry # name --> description
            an = id_
            description = name
            # ('GO:0000001', 'mitochondrion inheritance', ['GO:0048308', 'GO:0048311'], '"The distribution of mitochondria, including the mitochondrial genome, into daughter cells after mitosis or meiosis, mediated by interactions between mitochondria and the cytoskeleton." [GOC:mcc, PMID:10873824, PMID:11389764]')
            # ('KW-0001', '2Fe-2S', ['KW-0411', 'KW-0479'], '"Protein which contains at least one 2Fe-2S iron-sulfur cluster: 2 iron atoms complexed to 2 inorganic sulfides and 4 sulfur atoms of cysteines from the protein." []')
            if not is_upk:
                etype = str(get_entity_type_from_GO_term(id_, GO_dag))
            else:
                etype = "-51"

            if str(etype) == "-24": # don't need obsolete GO terms
                continue

            try:
                level = str(term_2_level_dict[an])
            except KeyError:
                level = "-1"
            line2write_func = etype + "\t" + an + "\t" + description + "\t" + year + "\t" + level + "\n"
            fh_funcs.write(line2write_func)

def get_entity_type_from_GO_term(term, GO_dag):
    if term == "GO:0003674" or GO_dag[term].has_parent("GO:0003674"):
        return "-23"
    elif term == "GO:0005575" or GO_dag[term].has_parent("GO:0005575"):
        return "-22"
    elif term == "GO:0008150" or GO_dag[term].has_parent("GO:0008150"):
        return "-21"
    else:
        return "-24"

def cut_long_string_at_word(string_, max_len_description=80):
    try:
        len_string = len(string_)
    except TypeError:
        return ""
    if len_string > max_len_description:
        string_2_use = ""
        for word in string_.split(" "):
            if len(string_2_use + word) > max_len_description:
                string_2_return = string_2_use.strip() + " ..."
                assert len(string_2_return) <= (max_len_description + 4)
                return string_2_return
            else:
                string_2_use += word + " "
    else:
        return string_.strip()

def clean_messy_string(string_):
    try:
        return re.sub('[^A-Za-z0-9\s]+', '', string_).replace("\n", " ").replace("\t", " ")
    except TypeError:
        return string_

def concatenate_Functions_tables(fn_list_str, fn_out, number_of_processes):
    # fn_list = [os.path.join(TABLES_DIR, fn) for fn in ["Functions_table_GO.txt", "Functions_table_UPK.txt", "Functions_table_KEGG.txt", "Functions_table_SMART.txt", "Functions_table_PFAM.txt", "Functions_table_InterPro.txt", "Functions_table_RCTM.txt"]]
    fn_list = [fn for fn in fn_list_str]
    # concatenate files
    fn_out_temp = fn_out + "_temp"
    tools.concatenate_files(fn_list, fn_out_temp)
    # sort
    tools.sort_file(fn_out_temp, fn_out_temp, number_of_processes=number_of_processes)
    # add functional enumeration column
    with open(fn_out_temp, "r") as fh_in:
        with open(fn_out, "w") as fh_out:
            for enum, line in enumerate(fh_in):
                fh_out.write(str(enum) + "\t" + line)

def concatenate_Functions_tables_no_enum(fn_list_str, fn_out, number_of_processes):
    # fn_list = [os.path.join(TABLES_DIR, fn) for fn in ["Functions_table_GO.txt", "Functions_table_UPK.txt", "Functions_table_KEGG.txt", "Functions_table_SMART.txt", "Functions_table_PFAM.txt", "Functions_table_InterPro.txt", "Functions_table_RCTM.txt"]]
    fn_list = [fn for fn in fn_list_str]
    # concatenate files
    fn_out_temp = fn_out + "_temp"
    tools.concatenate_files(fn_list, fn_out_temp)
    # sort
    tools.sort_file(fn_out_temp, fn_out_temp, number_of_processes=number_of_processes)
    # add functional enumeration column
    with open(fn_out_temp, "r") as fh_in:
        with open(fn_out, "w") as fh_out:
            for enum, line in enumerate(fh_in):
                fh_out.write(line)

def format_list_of_string_2_postgres_array(list_of_string):
    """
    removes internal spaces
    :param list_of_string: List of String
    :return: String
    """
    return "{" + str(sorted(set(list_of_string)))[1:-1].replace(" ", "").replace("'", '"') + "}"

def format_list_of_string_2_comma_separated(list_of_string):
    return ",".join(str(ele) for ele in sorted(set(list_of_string)))

def get_function_an_2_enum__and__enum_2_function_an_dict_from_flat_file(fn_Functions_table_STRING):
    function_2_enum_dict, enum_2_function_dict = {}, {}
    with open(fn_Functions_table_STRING, "r") as fh_in:
        for line in fh_in:
            line_split = line.split("\t")
            enum = line_split[0]
            function_ = line_split[2]
            function_2_enum_dict[function_] = enum
            enum_2_function_dict[enum] = function_
    return function_2_enum_dict, enum_2_function_dict

def Protein_2_FunctionEnum_table_STRING(fn_Functions_table_STRING, fn_in_Protein_2_function_table_STRING, fn_out_Protein_2_functionEnum_table_STRING, number_of_processes=1):
    function_2_enum_dict, enum_2_function_dict = get_function_an_2_enum__and__enum_2_function_an_dict_from_flat_file(fn_Functions_table_STRING)
    tools.sort_file(fn_in_Protein_2_function_table_STRING, fn_in_Protein_2_function_table_STRING, number_of_processes=number_of_processes)
    with open(fn_in_Protein_2_function_table_STRING, "r") as fh_in:
        with open(fn_out_Protein_2_functionEnum_table_STRING, "w") as fh_out:
            ENSP_last, function_arr_str, etype = fh_in.readline().strip().split("\t")
            function_arr = function_arr_str.replace(" ", "").split(",")
            functionEnum_list = _helper_format_array(function_arr_str.replace(" ", "").split(","), function_2_enum_dict)

            for line in fh_in:
                ENSP, function_arr_str, etype = line.strip().split("\t")
                function_arr = function_arr_str.replace(" ", "").split(",")

                if ENSP == ENSP_last:
                    functionEnum_list += _helper_format_array(function_arr, function_2_enum_dict)
                else:
                    if len(functionEnum_list) > 0:
                        # fh_out.write(ENSP_last + "\t" + format_list_of_string_2_postgres_array(functionEnum_list) + "\n") # etype is removed
                        fh_out.write(ENSP_last + "\t" + format_list_of_string_2_comma_separated(functionEnum_list) + "\n") # etype is removed
                    functionEnum_list = _helper_format_array(function_arr, function_2_enum_dict)

                ENSP_last = ENSP
            # fh_out.write(ENSP_last + "\t" + format_list_of_string_2_postgres_array(functionEnum_list) + "\n")  # etype is removed
            fh_out.write(ENSP_last + "\t" + format_list_of_string_2_comma_separated(functionEnum_list) + "\n")  # etype is removed

def _helper_format_array(function_arr, function_2_enum_dict):
    functionEnum_list = []
    for ele in function_arr:
        try:
            functionEnum_list.append(function_2_enum_dict[ele])
        except KeyError: # e.g. blacklisted terms
            # print("no translation for: {}".format(ele))
            return []
    return [int(ele) for ele in functionEnum_list]

def Lineage_table_STRING(fn_in_go_basic, fn_in_keywords, fn_in_rctm_hierarchy, fn_in_interpro_parent_2_child_tree, fn_in_functions, fn_out_lineage_table, fn_out_no_translation):
    lineage_dict = get_lineage_dict_for_all_entity_types_with_ontologies(fn_in_go_basic, fn_in_keywords, fn_in_rctm_hierarchy, fn_in_interpro_parent_2_child_tree)
    year_arr, hierlevel_arr, entitytype_arr, functionalterm_arr, indices_arr = get_lookup_arrays(fn_in_functions, low_memory=True)
    term_2_enum_dict = {key: val for key, val in zip(functionalterm_arr, indices_arr)}
    lineage_dict_enum = {}
    term_no_translation_because_obsolete = []
    for key, val in lineage_dict.items():
        try:
            key_enum = term_2_enum_dict[key]
        except KeyError:
            term_no_translation_because_obsolete.append(key)
            continue
        term_enum_temp = []
        for ele in val:
            try:
                term_enum_temp.append(term_2_enum_dict[ele])
            except KeyError:
                term_no_translation_because_obsolete.append(ele)
        lineage_dict_enum[key_enum] = sorted(term_enum_temp)
    keys_sorted = sorted(lineage_dict_enum.keys())
    with open(fn_out_lineage_table, "w") as fh_out:
        for key in keys_sorted:
            fh_out.write(str(key) + "\t" + "{" + str(sorted(set(lineage_dict_enum[key])))[1:-1].replace("'", '"') + "}\n")
    with open(fn_out_no_translation, "w") as fh_out_no_trans:
        for term in term_no_translation_because_obsolete:
            fh_out_no_trans.write(term + "\n")

def Lineage_table_STRING_v2_STRING_clusters(fn_in_GO_obo_Jensenlab, fn_in_go_basic, fn_in_keywords, fn_in_rctm_hierarchy, fn_in_interpro_parent_2_child_tree, fn_in_functions, fn_tree_STRING_clusters, fn_in_DOID_obo_Jensenlab, fn_in_BTO_obo_Jensenlab, fn_out_lineage_table, fn_out_lineage_table_hr, fn_out_no_translation):
    """
    GO_basic_obo = os.path.join(DOWNLOADS_DIR, "go-basic.obo")
    UPK_obo = os.path.join(DOWNLOADS_DIR, "keywords-all.obo")
    RCTM_hierarchy = os.path.join(DOWNLOADS_DIR, "RCTM_hierarchy.tsv")
    interpro_parent_2_child_tree = os.path.join(DOWNLOADS_DIR, "interpro_parent_2_child_tree.txt")
    Functions_table_STRING_reduced = os.path.join(TABLES_DIR, "Functions_table_STRING.txt") # reduced but not as suffix
    Lineage_table = os.path.join(TABLES_DIR, "Lineage_table_STRING.txt")
    Lineage_table_hr = os.path.join(TABLES_DIR, "Lineage_table_STRING_hr.txt")
    Lineage_table_no_translation = os.path.join(TABLES_DIR, "Lineage_table_no_translation.txt")
    fn_tree_STRING_clusters = os.path.join(DOWNLOADS_DIR, "clusters.tree.v11.0.txt.gz")
    Lineage_table_STRING_v2_STRING_clusters(GO_basic_obo, UPK_obo, RCTM_hierarchy, interpro_parent_2_child_tree, Functions_table_STRING_reduced, fn_tree_STRING_clusters. Lineage_table, Lineage_table_hr, Lineage_table_no_translation)
    """
    lineage_dict = get_lineage_dict_for_all_entity_types_with_ontologies(fn_in_GO_obo_Jensenlab, fn_in_keywords, fn_in_rctm_hierarchy, fn_in_DOID_obo_Jensenlab, fn_in_BTO_obo_Jensenlab, fn_in_interpro_parent_2_child_tree)
    
    # Jensenlab obo first, up-to-date GO_obo after to overwrite/update entries
    go_dag = obo_parser.GODag(obo_file=fn_in_go_basic)
    for go_term_name in go_dag:
        GOTerm_instance = go_dag[go_term_name]
        lineage_dict[go_term_name] = GOTerm_instance.get_all_parents()

    child_2_parent_dict_STRING_clusters = get_child_2_parent_dict_STRING_clusters(fn_tree_STRING_clusters)
    lineage_dict.update(get_lineage_from_child_2_direct_parent_dict(child_2_parent_dict_STRING_clusters))
    # lineage includes child. lineage_dict[child] = {child, parent_1, parent_2, ...}
    year_arr, hierlevel_arr, entitytype_arr, functionalterm_arr, indices_arr = get_lookup_arrays(fn_in_functions, low_memory=True)
    term_2_enum_dict = {key: val for key, val in zip(functionalterm_arr, indices_arr)}
    lineage_dict_enum = {}
    term_no_translation_because_obsolete = []
 
    for funcName, lineage in lineage_dict.items():  # lineage of funcNames
        try:
            funcEnum = term_2_enum_dict[funcName]
        except KeyError:
            term_no_translation_because_obsolete.append(funcName)
            continue
        term_enum_temp = []
        for funcName_temp in lineage:
            try:
                term_enum_temp.append(term_2_enum_dict[funcName_temp])
            except KeyError:
                term_no_translation_because_obsolete.append(funcName_temp)
        lineage_dict_enum[funcEnum] = sorted(term_enum_temp)

    with open(fn_out_lineage_table, "w") as fh_out:
        for key in sorted(lineage_dict_enum.keys()):
            lineage = lineage_dict_enum[key]
            if len(lineage) > 0:
                fh_out.write(str(key) + "\t" + ",".join(str(ele) for ele in sorted(set(lineage))) + "\n")

    with open(fn_out_lineage_table_hr, "w") as fh_out:
        for key in sorted(lineage_dict.keys()):
            fh_out.write(str(key) + "\t" + ",".join(str(ele) for ele in sorted(set(lineage_dict[key]))) + "\n")

    with open(fn_out_no_translation, "w") as fh_out_no_trans:
        for term in term_no_translation_because_obsolete:
            fh_out_no_trans.write(term + "\n")

def get_child_2_parent_dict_STRING_clusters(fn_tree):
    child_2_parent_dict = {} # direct parents
    # ncbi_taxid     child_cluster_id        parent_cluster_id
    gen = tools.yield_line_uncompressed_or_gz_file(fn_tree)
    _ = next(gen)
    for line in gen:
        ncbi_taxid, child_cluster_id, parent_cluster_id = line.split()
        child = ncbi_taxid + "_" + child_cluster_id
        parent = ncbi_taxid + "_" + parent_cluster_id
        if child not in child_2_parent_dict:
            child_2_parent_dict[child] = {parent}
        else:
            child_2_parent_dict[child] |= {parent}
    return child_2_parent_dict

def get_lineage_dict_for_all_entity_types_with_ontologies(fn_go_basic_obo, fn_keywords_obo, fn_rctm_hierarchy, fn_in_DOID_obo_Jensenlab, fn_in_BTO_obo_Jensenlab, fn_in_interpro_parent_2_child_tree):
    lineage_dict = {}
    go_dag = obo_parser.GODag(obo_file=fn_go_basic_obo)
    upk_dag = obo_parser.GODag(obo_file=fn_keywords_obo, upk=True)
    # key=GO-term, val=set of GO-terms (parents)
    for go_term_name in go_dag:
        GOTerm_instance = go_dag[go_term_name]
        # lineage_dict[go_term_name] = GOTerm_instance.get_all_parents().union(GOTerm_instance.get_all_children()) # wrong for this use case
        lineage_dict[go_term_name] = GOTerm_instance.get_all_parents()
    for term_name in upk_dag:
        Term_instance = upk_dag[term_name]
        lineage_dict[term_name] = Term_instance.get_all_parents()

    bto_dag = obo_parser.GODag(obo_file=fn_in_BTO_obo_Jensenlab)
    for term_name in bto_dag:
        Term_instance = bto_dag[term_name]
        lineage_dict[term_name ] = Term_instance.get_all_parents()
    doid_dag = obo_parser.GODag(obo_file=fn_in_DOID_obo_Jensenlab)
    for term_name in doid_dag:
        Term_instance = doid_dag[term_name]
        lineage_dict[term_name ] = Term_instance.get_all_parents()        

    # lineage_dict.update(get_lineage_Reactome(fn_rctm_hierarchy))
    child_2_parent_dict = get_child_2_direct_parent_dict_RCTM(fn_rctm_hierarchy)
    lineage_dict.update(get_lineage_from_child_2_direct_parent_dict(child_2_parent_dict))

    child_2_parent_dict, term_2_level_dict = get_child_2_direct_parents_and_term_2_level_dict_interpro(fn_in_interpro_parent_2_child_tree)
    lineage_dict.update(get_lineage_from_child_2_direct_parent_dict(child_2_parent_dict))
    return lineage_dict

def get_parent_2_direct_children_dict(fn_GO_obo_Jensenlab, fn_go_basic_obo, fn_keywords_obo, fn_rctm_hierarchy, fn_in_interpro_parent_2_child_tree, fn_tree_STRING_clusters, fn_DOID_obo_Jensenlab, fn_BTO_obo_Jensenlab):
    child_2_parent_dict, parent_2_child_dict = {}, {}
    child_2_parent_dict.update(get_child_2_parent_dict_STRING_clusters(fn_tree_STRING_clusters))
    child_2_parent_dict.update(get_child_2_direct_parent_dict_from_dag(obo_parser.GODag(obo_file=fn_go_basic_obo)))
    child_2_parent_dict.update(get_child_2_direct_parent_dict_from_dag(obo_parser.GODag(obo_file=fn_GO_obo_Jensenlab)))
    child_2_parent_dict.update(get_child_2_direct_parent_dict_from_dag(obo_parser.GODag(obo_file=fn_keywords_obo, upk=True)))
    child_2_parent_dict.update(get_child_2_direct_parent_dict_RCTM(fn_rctm_hierarchy))

    child_2_parent_dict.update(get_child_2_direct_parent_dict_from_dag(obo_parser.GODag(obo_file=fn_DOID_obo_Jensenlab)))
    child_2_parent_dict.update(get_child_2_direct_parent_dict_from_dag(obo_parser.GODag(obo_file=fn_BTO_obo_Jensenlab)))

    child_2_parent_dict_temp, _ = get_child_2_direct_parents_and_term_2_level_dict_interpro(fn_in_interpro_parent_2_child_tree)
    child_2_parent_dict.update(child_2_parent_dict_temp)

    for child, parents_list in child_2_parent_dict.items():
        for parent in parents_list:
            if parent not in parent_2_child_dict:
                parent_2_child_dict[parent] = [child]
            else:
                parent_2_child_dict[parent].append(child)
    return parent_2_child_dict

def get_lineage_from_child_2_direct_parent_dict(child_2_direct_parent_dict):
    lineage_dict = defaultdict(lambda: set())
    for child in child_2_direct_parent_dict:
        parents = get_parents_iterative(child, child_2_direct_parent_dict)
        if child in lineage_dict:
            lineage_dict[child].union(parents)
        else:
            lineage_dict[child] = parents
    return lineage_dict

def get_child_2_direct_parent_dict_RCTM(fn_in):
    """
    child_2_parent_dict --> child 2 direct parents
    R-BTA-109581    R-BTA-109606
    R-BTA-109581    R-BTA-169911
    R-BTA-109581    R-BTA-5357769
    """
    child_2_parent_dict = {}
    with open(fn_in, "r") as fh_in:
        for line in fh_in:
            parent, child = line.split("\t")
            parent = parent[2:]
            child = child[2:].strip()
            if child not in child_2_parent_dict:
                child_2_parent_dict[child] = {parent}
            else:
                child_2_parent_dict[child] |= {parent}
    return child_2_parent_dict

def get_lookup_arrays(fn_in_functions, low_memory):
    """
    funcEnum_2_hierarchical_level
    simple numpy array of hierarchical levels
    if -1 in DB --> convert to np.nan since these are missing values
    # - funcEnum_2_year
    # - funcEnum_2_hierarchical_level
    # - funcEnum_2_etype
    # - funcEnum_2_description
    # - funcEnum_2_term
    :param fn_in_functions: String (file name for functions_table)
    :param low_memory: Bool flag to return description_array
    :return: immutable numpy array of int
    """
    result = yield_split_line_from_file(fn_in_functions, line_numbers=True)
    shape_ = next(result)
    year_arr = np.full(shape=shape_, fill_value=-1, dtype="int16")  # Integer (-32768 to 32767)
    entitytype_arr = np.full(shape=shape_, fill_value=0, dtype="int8")
    if not low_memory:
        description_arr = np.empty(shape=shape_, dtype=object) # ""U261"))
        # category_arr = np.empty(shape=shape_, dtype=np.dtype("U49"))  # description of functional category (e.g. "Gene Ontology biological process")
        category_arr = np.empty(shape=shape_, dtype=object)  # description of functional category (e.g. "Gene Ontology biological process")
    functionalterm_arr = np.empty(shape=shape_, dtype=object) #np.dtype("U13"))
    hierlevel_arr = np.full(shape=shape_, fill_value=-1, dtype="int8")  # Byte (-128 to 127)
    indices_arr = np.arange(shape_, dtype=np.dtype("uint32"))
    indices_arr.flags.writeable = False

    for res in result:
        func_enum, etype, term, description, year, hierlevel = res
        func_enum = int(func_enum)
        etype = int(etype)
        try:
            year = int(year)
        except ValueError: # e.g. "...."
            year = -1
        hierlevel = int(hierlevel)
        entitytype_arr[func_enum] = etype
        functionalterm_arr[func_enum] = term
        year_arr[func_enum] = year
        hierlevel_arr[func_enum] = hierlevel
        if not low_memory:
            description_arr[func_enum] = description
            category_arr[func_enum] = variables.entityType_2_functionType_dict[etype]

    year_arr.flags.writeable = False # make it immutable
    hierlevel_arr.flags.writeable = False
    entitytype_arr.flags.writeable = False
    functionalterm_arr.flags.writeable = False
    if not low_memory:
        description_arr.flags.writeable = False
        category_arr.flags.writeable = False
        return year_arr, hierlevel_arr, entitytype_arr, functionalterm_arr, indices_arr, description_arr, category_arr
    else:
        return year_arr, hierlevel_arr, entitytype_arr, functionalterm_arr, indices_arr

def yield_split_line_from_file(fn_in, line_numbers=False, split_on="\t"):
    if line_numbers:
        num_lines = tools.line_numbers(fn_in)
        yield num_lines

    with open(fn_in, "r") as fh_in:
        for line in fh_in:
            line_split = line.split(split_on)
            line_split[-1] = line_split[-1].strip()
            yield line_split

def Taxid_2_Proteins_table(fn_in_protein_shorthands, fn_out_Taxid_2_Proteins_table_STRING, number_of_processes=1, verbose=True):
    if verbose:
        print("Creating Taxid_2_Proteins_table.txt")
        print("protein_shorthands needs sorting, doing it now")
    tools.sort_file(fn_in_protein_shorthands, fn_in_protein_shorthands, columns="1", number_of_processes=number_of_processes, verbose=verbose)
    if verbose:
        print("parsing protein_shorthands")
    # now parse and transform into wide format
    with open(fn_in_protein_shorthands, "r") as fh_in:
        with open(fn_out_Taxid_2_Proteins_table_STRING, "w") as fh_out:
            ENSP_list = []
            did_first = False
            for line in fh_in:
                # 287.DR97_1012   6412
                # 287.DR97_1013   6413
                ENSP, *rest = line.strip().split()
                TaxID = ENSP[:ENSP.index(".")]
                if not did_first:
                    TaxID_previous = TaxID
                    did_first = True
                if TaxID == TaxID_previous:
                    ENSP_list.append(ENSP)
                else:
                    ENSPs_2_write = sorted(set(ENSP_list))
                    fh_out.write(TaxID_previous +  "\t" + format_list_of_string_2_postgres_array(ENSPs_2_write) + "\t" + str(len(ENSPs_2_write)) + "\n")
                    #fh_out.write(TaxID_previous + "\t" + str(len(ENSPs_2_write)) + "\t" + format_list_of_string_2_comma_separated(ENSPs_2_write) + "\n")
                    ENSP_list = [ENSP]
                    TaxID_previous = TaxID
            ENSPs_2_write = sorted(set(ENSP_list))
            fh_out.write(TaxID_previous + "\t" + format_list_of_string_2_postgres_array(ENSPs_2_write) + "\t" + str(len(ENSPs_2_write)) + "\n")
            #fh_out.write(TaxID_previous + "\t" + str(len(ENSPs_2_write)) + "\t" + format_list_of_string_2_comma_separated(ENSPs_2_write) + "\n")

def Taxid_2_FunctionCountArray_table_STRING(Protein_2_FunctionEnum_table_STRING, Functions_table_STRING, Taxid_2_Proteins_table, fn_out_Taxid_2_FunctionCountArray_table_STRING, number_of_processes=1):
    # - sort Protein_2_FunctionEnum_table_STRING.txt
    # - create array of zeros of function_enumeration_length
    # - for line in Protein_2_FunctionEnum_table_STRING
    #     add counts to array until taxid_new != taxid_previous
    print("create_Taxid_2_FunctionCountArray_table_STRING")
    tools.sort_file(Protein_2_FunctionEnum_table_STRING, Protein_2_FunctionEnum_table_STRING, number_of_processes=number_of_processes)
    taxid_2_total_protein_count_dict = _helper_get_taxid_2_total_protein_count_dict(Taxid_2_Proteins_table)
    num_lines = tools.line_numbers(Functions_table_STRING)
    with open(fn_out_Taxid_2_FunctionCountArray_table_STRING, "w") as fh_out:
        with open(Protein_2_FunctionEnum_table_STRING, "r") as fh_in:
            funcEnum_count_background = np.zeros(shape=num_lines, dtype=np.dtype("uint32"))
            line = next(fh_in)
            fh_in.seek(0)
            taxid_previous, ENSP, funcEnum_set = helper_parse_line_Protein_2_FunctionEnum_table_STRING(line)

            for line in fh_in:
                taxid, ENSP, funcEnum_set = helper_parse_line_Protein_2_FunctionEnum_table_STRING(line)
                if taxid != taxid_previous:
                    index_backgroundCount_array_string = helper_format_funcEnum(funcEnum_count_background, min_count=2)
                    if not taxid_previous in taxid_2_total_protein_count_dict.keys():
                        taxid_previous = taxid
                        continue
                    background_n = taxid_2_total_protein_count_dict[taxid_previous]
                    fh_out.write(taxid_previous + "\t" + background_n + "\t" + index_backgroundCount_array_string + "\n")
                    funcEnum_count_background = np.zeros(shape=num_lines, dtype=np.dtype("uint32"))

                funcEnum_count_background = helper_count_funcEnum(funcEnum_count_background, funcEnum_set)
                taxid_previous = taxid
            index_backgroundCount_array_string = helper_format_funcEnum(funcEnum_count_background, min_count=2)
            background_n = taxid_2_total_protein_count_dict[taxid]
            fh_out.write(taxid + "\t" + background_n + "\t" + index_backgroundCount_array_string + "\n")
    print("Taxid_2_FunctionCountArray_table_STRING done :)")

def helper_parse_line_Protein_2_FunctionEnum_table_STRING(line):
    ENSP, funcEnum_set = line.strip().split("\t")
    funcEnum_set = {int(num) for num in funcEnum_set.replace(" ", "").split(",")}
    taxid = ENSP.split(".")[0]
    return taxid, ENSP, funcEnum_set

def helper_count_funcEnum(funcEnum_count, funcEnum_set):
    for funcEnum in funcEnum_set:
        funcEnum_count[funcEnum] += 1
    return funcEnum_count

def helper_format_funcEnum(funcEnum_count_background, min_count=2):
    enumeration_arr = np.arange(0, funcEnum_count_background.shape[0])
    cond = funcEnum_count_background >= min_count
    funcEnum_count_background = funcEnum_count_background[cond]
    enumeration_arr = enumeration_arr[cond]
    string_2_write = ""
    # for ele in zip(enumeration_arr, funcEnum_count_background):
    #     string_2_write += "{{{0},{1}}},".format(ele[0], ele[1])
    # index_backgroundCount_array_string = "{" + string_2_write[:-1] + "}"
    index_backgroundCount_array_string = ",".join(str(ele) for ele in list(enumeration_arr)) + "\t" + ",".join(str(ele) for ele in list(funcEnum_count_background))
    return index_backgroundCount_array_string

def Protein_2_Function_table_KEGG(fn_in_kegg_benchmarking, fn_out_Protein_2_Function_table_KEGG, fn_out_KEGG_TaxID_2_acronym_table, number_of_processes=1):
    fn_out_temp = fn_out_Protein_2_Function_table_KEGG + "_temp"
    # create long format of ENSP 2 KEGG table
    taxid_2_acronym_dict = {}
    with open(fn_in_kegg_benchmarking, "r") as fh_in:
        with open(fn_out_temp, "w") as fh_out:
            for line in fh_in:
                TaxID, KEGG, num_ENSPs, *ENSPs = line.split()
                if KEGG.startswith("CONN_"):
                    continue
                else: # e.g. bced00190 or rhi00290
                    match = re.search("\d", KEGG)
                    if match:
                        index_ = match.start()
                        acro = KEGG[:index_]
                        taxid_2_acronym_dict[TaxID] = acro
                    KEGG = KEGG[-5:]
                # add TaxID to complete the ENSP
                ENSPs = [TaxID + "." + ENSP for ENSP in ENSPs]
                for ENSP in ENSPs:
                    fh_out.write(ENSP + "\t" + "map" + KEGG + "\n")
    with open(fn_out_KEGG_TaxID_2_acronym_table, "w") as fh_acro:
        for taxid, acronym in taxid_2_acronym_dict.items():
            fh_acro.write(taxid + "\t" + acronym + "\n")

    # sort by first column and transform to wide format
    tools.sort_file(fn_out_temp, fn_out_temp, columns="1", number_of_processes=number_of_processes)

    # convert long to wide format and add entity type
    entityType_UniProtKeywords = variables.id_2_entityTypeNumber_dict["KEGG"]
    long_2_wide_format(fn_out_temp, fn_out_Protein_2_Function_table_KEGG, entityType_UniProtKeywords)

def long_2_wide_format(fn_in, fn_out, etype=None):
    function_list = []
    with open(fn_in, "r") as fh_in:
        with open(fn_out, "w") as fh_out:
            an_last, function_ = fh_in.readline().strip().split("\t")
            function_list.append(function_)
            for line in fh_in:
                an, function_ = line.strip().split("\t")
                if an == an_last:
                    function_list.append(function_)
                else:
                    if etype is None:
                        fh_out.write(an_last + "\t{" + ','.join('"' + item + '"' for item in sorted(set(function_list))) + "}\n")
                    else:
                        fh_out.write(an_last + "\t{" + ','.join('"' + item + '"' for item in sorted(set(function_list))) + "}\t" + etype + "\n")

                    function_list = []
                    an_last = an
                    function_list.append(function_)
            if etype is None:
                fh_out.write(an + "\t{" + ','.join('"' + item + '"' for item in sorted(set(function_list))) + "}\n")
            else:
                fh_out.write(an + "\t{" + ','.join('"' + item + '"' for item in sorted(set(function_list))) + "}\t" + etype + "\n")

def Protein_2_Function_table_SMART_and_PFAM_temp(fn_in_dom_prot_full, fn_in_map_name_2_an_SMART, fn_in_map_name_2_an_PFAM, fn_out_SMART_temp, fn_out_PFAM_temp, number_of_processes=1, verbose=True):
    """
    :param fn_in_dom_prot_full: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/downloads/string11_dom_prot_full.sql)
    :param fn_out_SMART_temp: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/Protein_2_Function_table_SMART.txt)
    :param fn_out_PFAM_temp: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/Protein_2_Function_table_PFAM.txt)
    :param number_of_processes: Integer (number of cores, shouldn't be too high since Disks are probably the bottleneck even with SSD, e.g. max 8 !?)
    :param verbose: Bool (flag to print infos)
    :return: None
    """
    if verbose:
        print("\ncreate_Protein_2_Functions_table_SMART and PFAM")
    tools.sort_file(fn_in_dom_prot_full, fn_in_dom_prot_full, columns="2", number_of_processes=number_of_processes)
    if verbose:
        print("parsing previous result to produce create_Protein_2_Function_table_SMART.txt and Protein_2_Function_table_PFAM.txt")
    entityType_SMART = variables.id_2_entityTypeNumber_dict["SMART"]
    entityType_PFAM = variables.id_2_entityTypeNumber_dict["PFAM"]

    with open(fn_out_PFAM_temp, "w") as fh_out_PFAM:
        with open(fn_out_SMART_temp, "w") as fh_out_SMART:
            for ENSP, PFAM_list_SMART_list in parse_string11_dom_prot_full_yield_entry(fn_in_dom_prot_full):
                PFAM_list, SMART_list = PFAM_list_SMART_list
                PFAM_list  = map_list(PFAM_list, fn_in_map_name_2_an_PFAM) # map domains using map_name_2_an files
                SMART_list = map_list(SMART_list, fn_in_map_name_2_an_SMART)
                if len(PFAM_list) >= 1:
                    fh_out_PFAM.write(ENSP + "\t" + "{" + str(PFAM_list)[1:-1].replace(" ", "").replace("'", '"') + "}\t" + entityType_PFAM + "\n")
                if len(SMART_list) >= 1:
                    fh_out_SMART.write(ENSP + "\t" + "{" + str(SMART_list)[1:-1].replace(" ", "").replace("'", '"') + "}\t" + entityType_SMART + "\n")
    if verbose:
        print("done create_Protein_2_Function_table_SMART\n")

def map_list (to_be_mapped_list, fn_in_map_name_2_an):
    mapping_dict = {}
    with open(fn_in_map_name_2_an, "r") as fh_in:
        for line in fh_in:
            name, an = line.split()
            mapping_dict[name] = an
    mapped_list = []
    for l in to_be_mapped_list:
        if l in mapping_dict.keys():
            mapped_list.append(mapping_dict[l])
        else:
            mapped_list.append(l)
    return mapped_list

def parse_string11_dom_prot_full_yield_entry(fn_in):
    domain_list = []
    did_first = False
    ENSP_previous = ""
    counter = 0
    with open(fn_in, "r") as fh_in:
        for line in fh_in:
            counter += 1
            domain, ENSP, *rest = line.split()
            if not did_first:
                ENSP_previous = ENSP
                did_first = True
            if ENSP == ENSP_previous:
                domain_list.append(domain)
            else:
                yield (ENSP_previous, sort_PFAM_and_SMART(domain_list))
                domain_list = [domain]
                ENSP_previous = ENSP
        yield (ENSP_previous, sort_PFAM_and_SMART(domain_list))

def sort_PFAM_and_SMART(list_of_domain_names):
    PFAM_list, SMART_list = [], []
    for domain in set(list_of_domain_names):
        if domain.startswith("Pfam:"):
            PFAM_list.append(domain.replace("Pfam:", ""))
        elif domain in {"TRANS", "COIL", "SIGNAL"}:
            continue
        else:
            SMART_list.append(domain)
    return sorted(PFAM_list), sorted(SMART_list)

def Protein_2_Function_table_GO(fn_in_obo_file, fn_in_knowledge, fn_out_Protein_2_Function_table_GO, number_of_processes=1, verbose=True):
    """
    secondary GOids are converted to primary GOids
    e.g. goterm: 'GO:0007610' has secondary id 'GO:0044708', thus if 'GO:0044708' is associated it will be mapped to 'GO:0007610'
    :param fn_in_obo_file: String (file name for obo file)
    :param fn_in_knowledge: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/downloads/knowledge.tsv.gz)
    :param fn_out_Protein_2_Function_table_GO: String (e.g. /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/Protein_2_Function_table_GO.txt)
    :param number_of_processes: Integer (number of cores, shouldn't be too high since Disks are probably the bottleneck even with SSD, e.g. max 4)
    :param verbose: Bool (flag to print infos)
    :return: None
    """
    ### e.g. of lines
    # 1001530 PMSV_1450       -21     GO:0000302      UniProtKB-EC    IEA     2       FALSE   http://www.uniprot.org/uniprot/SODF_PHOLE
    # 1000565 METUNv1_03599   -23     GO:0003824      UniProtKB-EC    IEA     2       FALSE   http://www.uniprot.org/uniprot/GMAS_METUF
    if verbose:
        print("\ncreate_Protein_2_Function_table_GO")
    GO_dag = obo_parser.GODag(obo_file=fn_in_obo_file, upk=False)
    tools.sort_file(fn_in_knowledge, fn_in_knowledge, columns="1,2", number_of_processes=number_of_processes)
    if verbose:
        print("sorting {}".format(fn_in_knowledge))
    GOterms_not_in_obo = []
    if verbose:
        print("parsing previous result to produce Protein_2_Function_table_GO.txt")
    with open(fn_out_Protein_2_Function_table_GO, "w") as fh_out:
        for ENSP, GOterm_list, _ in parse_string_go_yield_entry(fn_in_knowledge):
            GOterm_list, GOterms_not_in_obo_temp = get_all_parent_terms(GOterm_list, GO_dag)
            GOterms_not_in_obo += GOterms_not_in_obo_temp
            if len(GOterm_list) >= 1:
                MFs, CPs, BPs, not_in_OBO = divide_into_categories(GOterm_list, GO_dag, [], [], [], [])
                GOterms_not_in_obo_temp += not_in_OBO
                if MFs:
                    fh_out.write(ENSP + "\t" + "{" + str(MFs)[1:-1].replace(" ", "").replace("'", '"') + "}\t" + variables.id_2_entityTypeNumber_dict['GO:0003674'] + "\n") # 'Molecular Function', -23
                if CPs:
                    fh_out.write(ENSP + "\t" + "{" + str(CPs)[1:-1].replace(" ", "").replace("'", '"') + "}\t" + variables.id_2_entityTypeNumber_dict['GO:0005575'] + "\n") # 'Cellular Component', -22
                if BPs:
                    fh_out.write(ENSP + "\t" + "{" + str(BPs)[1:-1].replace(" ", "").replace("'", '"') + "}\t" + variables.id_2_entityTypeNumber_dict['GO:0008150'] + "\n") # 'Biological Process', -21
    GOterms_not_in_obo = sorted(set(GOterms_not_in_obo))
    fn_log = os.path.join(LOG_DIRECTORY, "create_SQL_tables_GOterms_not_in_OBO.log")
    with open(fn_log, "w") as fh_out:
        fh_out.write(";".join(GOterms_not_in_obo))
    if verbose:
        print("Number of GO terms not in OBO: ", len(GOterms_not_in_obo))
        print("done create_Protein_2_Function_table_GO\n")

def parse_string_go_yield_entry(fn_in):
    """
    careful the entity type will NOT (necessarily) be consistent as multiple annotations are given
    :param fn_in:
    :return:
    """
    # "9606    ENSP00000281154 -24     GO:0019861      UniProtKB       CURATED 5       TRUE    http://www.uniprot.org/uniprot/ADT4_HUMAN"
    GOterm_list = []
    did_first = False
    for line in tools.yield_line_uncompressed_or_gz_file(fn_in):
        TaxID, ENSP_without_TaxID, EntityType, GOterm, *rest = line.split()
        if not GOterm.startswith("GO:"):
            continue
        ENSP = TaxID + "." + ENSP_without_TaxID
        if not did_first:
            ENSP_previous = ENSP
            did_first = True
        if ENSP == ENSP_previous:
            GOterm_list.append(GOterm)
        else:
            yield (ENSP_previous, GOterm_list, EntityType)
            GOterm_list = [GOterm]
            ENSP_previous = ENSP
    yield (ENSP_previous, GOterm_list, EntityType)

def get_all_parent_terms(GOterm_list, GO_dag):
    """
    backtracking to root INCLUDING given children
    :param GOterm_list: List of String
    :param GO_dag: Dict like object
    :return: List of String
    """
    parents = []
    not_in_obo = []
    for GOterm in GOterm_list:
        try:
            parents += GO_dag[GOterm].get_all_parents()
        except KeyError: # remove GOterm from DB since not in OBO
            not_in_obo.append(GOterm)
    return sorted(set(parents).union(set(GOterm_list))), sorted(set(not_in_obo))

def divide_into_categories(GOterm_list, GO_dag,
                           MFs=[], CPs=[], BPs=[], not_in_OBO=[]):
    """
    split a list of GO-terms into the 3 parent categories in the following order MFs, CPs, BPs
    'GO:0003674': "-23",  # 'Molecular Function',
    'GO:0005575': "-22",  # 'Cellular Component',
    'GO:0008150': "-21",  # 'Biological Process',
    :param GOterm_list: List of String
    :param GO_dag: Dict like object
    :return: Tuple (List of String x 3)
    """
#     MFs, CPs, BPs, not_in_OBO = [], [], [], []
    for term in GOterm_list:
        if term == "GO:0003674" or GO_dag[term].has_parent("GO:0003674"):
            MFs.append(GO_dag[term].id)
        elif term == "GO:0005575" or GO_dag[term].has_parent("GO:0005575"):
            CPs.append(GO_dag[term].id)
        elif term == "GO:0008150" or GO_dag[term].has_parent("GO:0008150"):
            BPs.append(GO_dag[term].id)
        else:
            try:
                GO_id = GO_dag[term].id
            except KeyError:
                not_in_OBO.append(term)
                continue
            if GO_dag[GO_id].is_obsolete:
                not_in_OBO.append(term)
            else:
                MFs, CPs, BPs, not_in_OBO = divide_into_categories([GO_id], GO_dag, MFs, CPs, BPs, not_in_OBO)
    return sorted(MFs), sorted(CPs), sorted(BPs), sorted(not_in_OBO)

def Protein_2_Function_table_UniProtKeyword(fn_in_Functions_table_UPK, fn_in_obo, fn_in_uniprot_SwissProt_dat, fn_in_uniprot_TrEMBL_dat, fn_in_uniprot_2_string, fn_out_Protein_2_Function_table_UPK, number_of_processes=1,  verbose=True):
    if verbose:
        print("\ncreate_Protein_2_Function_table_UniProtKeywords")
    UPK_dag = obo_parser.GODag(obo_file=fn_in_obo, upk=True)
    UPK_Name_2_AN_dict = get_keyword_2_upkan_dict(fn_in_Functions_table_UPK)  # depends on create_Child_2_Parent_table_UPK__and__Functions_table_UPK__and__Function_2_definition_UPK
    uniprot_2_string_missing_mapping = []
    uniprot_2_ENSPs_dict = parse_full_uniprot_2_string(fn_in_uniprot_2_string)
    entityType_UniProtKeywords = variables.id_2_entityTypeNumber_dict["UniProtKeywords"]
    UPKs_not_in_obo_list = []
    # import ipdb
    # ipdb.set_trace()
    with open(fn_out_Protein_2_Function_table_UPK, "w") as fh_out:
        if verbose:
            print("parsing {}".format(fn_in_uniprot_SwissProt_dat))
        for UniProtAN_list, KeyWords_list in parse_uniprot_dat_dump_yield_entry(fn_in_uniprot_SwissProt_dat):
            for UniProtAN in UniProtAN_list:
                try:
                    ENSP_list = uniprot_2_ENSPs_dict[UniProtAN]
                except KeyError:
                    uniprot_2_string_missing_mapping.append(UniProtAN)
                    continue
                for ENSP in ENSP_list:
                    if len(KeyWords_list) >= 1:
                        UPK_ANs, UPKs_not_in_obo_temp = map_keyword_name_2_AN(UPK_Name_2_AN_dict, KeyWords_list)
                        UPKs_not_in_obo_list += UPKs_not_in_obo_temp
                        UPK_ANs, UPKs_not_in_obo_temp = get_all_parent_terms(UPK_ANs, UPK_dag)
                        UPKs_not_in_obo_list += UPKs_not_in_obo_temp
                    else:
                        continue
                    if len(UPK_ANs) >= 1:
                        fh_out.write(ENSP + "\t" + "{" + str(sorted(UPK_ANs))[1:-1].replace(" ", "").replace("'", '"') + "}\t" + entityType_UniProtKeywords + "\n")

        if verbose:
            print("parsing {}".format(fn_in_uniprot_TrEMBL_dat))
        for UniProtAN_list, KeyWords_list in parse_uniprot_dat_dump_yield_entry(fn_in_uniprot_TrEMBL_dat):
            for UniProtAN in UniProtAN_list:
                try:
                    ENSP_list = uniprot_2_ENSPs_dict[UniProtAN]
                except KeyError:
                    uniprot_2_string_missing_mapping.append(UniProtAN)
                    continue
                for ENSP in ENSP_list:
                    if len(KeyWords_list) >= 1:
                        UPK_ANs, UPKs_not_in_obo_temp = map_keyword_name_2_AN(UPK_Name_2_AN_dict, KeyWords_list)
                        UPKs_not_in_obo_list += UPKs_not_in_obo_temp
                        UPK_ANs, UPKs_not_in_obo_temp = get_all_parent_terms(UPK_ANs, UPK_dag)
                        UPKs_not_in_obo_list += UPKs_not_in_obo_temp
                    else:
                        continue
                    if len(UPK_ANs) >= 1:
                        fh_out.write(ENSP + "\t" + "{" + str(sorted(UPK_ANs))[1:-1].replace(" ", "").replace("'", '"') + "}\t" + entityType_UniProtKeywords + "\n")

    ### table Protein_2_Function_table_UniProtKeywords.txt needs sorting
    tools.sort_file(fn_out_Protein_2_Function_table_UPK, fn_out_Protein_2_Function_table_UPK, columns="1", number_of_processes=number_of_processes, verbose=verbose)

    UPKs_not_in_obo_list = sorted(set(UPKs_not_in_obo_list))
    fn_log = os.path.join(LOG_DIRECTORY, "create_SQL_tables_UniProtKeywords_not_in_OBO.log")
    with open(fn_log, "w") as fh_out:
        fh_out.write(";".join(UPKs_not_in_obo_list))

    if len(uniprot_2_string_missing_mapping) > 0:
        print("#!$%^@"*80)
        print("writing uniprot_2_string_missing_mapping to log file\n", os.path.join(LOG_DIRECTORY, "create_SQL_tables_STRING.log"))
        print("number of uniprot_2_string_missing_mapping", len(uniprot_2_string_missing_mapping))
        print("number of uniprot_2_ENSPs_dict keys", len(uniprot_2_ENSPs_dict.keys()))
        print("#!$%^@" * 80)
        with open(os.path.join(LOG_DIRECTORY, "create_SQL_tables_STRING.log"), "a+") as fh:
            fh.write(";".join(uniprot_2_string_missing_mapping))

    if verbose:
        print("Number of UniProt Keywords not in OBO: ", len(UPKs_not_in_obo_list))
        print("done create_Protein_2_Function_table_UniProtKeywords\n")

def parse_full_uniprot_2_string(fn_in):
    """
    #species   uniprot_ac|uniprot_id   string_id   identity   bit_score
    742765  G1WQX1|G1WQX1_9FIRM     742765.HMPREF9457_01522 100.0   211.0
    742765  G1WQX2|G1WQX2_9FIRM     742765.HMPREF9457_01523 100.0   70.5
    """
    uniprot_2_ENSPs_dict = {}
    with open(fn_in, "r") as fh:
        next(fh) # skip header line
        for line in fh:
            taxid, uniprot_ac_and_uniprot_id, ENSP, *rest= line.strip().split()
            uniprot = uniprot_ac_and_uniprot_id.split("|")[0]
            if not uniprot in uniprot_2_ENSPs_dict :
                uniprot_2_ENSPs_dict[uniprot] = [ENSP]
            else: # it can be a one to many mapping (1 UniProtAN to multiple ENSPs)
                uniprot_2_ENSPs_dict[uniprot].append(ENSP)
    return uniprot_2_ENSPs_dict

def get_keyword_2_upkan_dict(Functions_table_UPK):
    """
    UniProt-keyword 2 UPK-AccessionNumber
    :return: Dict(String2String)
    """
    keyword_2_upkan_dict = {}
    with open(Functions_table_UPK, "r") as fh:
        for line in fh:
            line_split = line.strip().split("\t")
            keyword = line_split[2]
            upkan = line_split[1]
            keyword_2_upkan_dict[keyword] = upkan
    return keyword_2_upkan_dict

def parse_uniprot_dat_dump_yield_entry(fn_in):
    """
    yield parsed entry from UniProt DB dump file
    :param fn_in:
    :return:
    """
    for entry in yield_entry_UniProt_dat_dump(fn_in):
        UniProtAN_list, UniProtAN, Keywords_string = [], "", ""
        for line in entry:
            line_code = line[:2]
            rest = line[2:].strip()
            if line_code == "AC":
                UniProtAN_list += [UniProtAN.strip() for UniProtAN in rest.split(";") if len(UniProtAN) > 0]
            elif line_code == "KW":
                Keywords_string += rest
        UniProtAN_list = sorted(set(UniProtAN_list))
        Keywords_list = sorted(set(Keywords_string.split(";")))
        # remove empty strings from keywords_list
        Keywords_list = [cleanup_Keyword(keyword) for keyword in Keywords_list if len(keyword) > 0]
        yield (UniProtAN_list, Keywords_list)

def map_keyword_name_2_AN(UPK_Name_2_AN_dict, KeyWords_list):
    UPK_ANs, UPKs_not_in_obo_temp = [], []
    for keyword in KeyWords_list:
        try:
            AN = UPK_Name_2_AN_dict[keyword]
        except KeyError:
            UPKs_not_in_obo_temp.append(keyword)
            continue
        UPK_ANs.append(AN)
    return UPK_ANs, UPKs_not_in_obo_temp

def cleanup_Keyword(keyword):
    """
    remove stuff after '{'
    remove '.' at last keyword
    remove last ',' in string
    "ATP-binding{ECO:0000256|HAMAP-Rule:MF_00175,","Chaperone{ECO:0000256|HAMAP-Rule:MF_00175,","Completeproteome{ECO:0000313|Proteomes:UP000005019}","ECO:0000256|SAAS:SAAS00645729}","ECO:0000256|SAAS:SAAS00645733}","ECO:0000256|SAAS:SAAS00645738}.","ECO:0000256|SAAS:SAAS00701776}","ECO:0000256|SAAS:SAAS00701780,ECO:0000313|EMBL:EGK73413.1}","Hydrolase{ECO:0000313|EMBL:EGK73413.1}","Metal-binding{ECO:0000256|HAMAP-Rule:MF_00175,","Nucleotide-binding{ECO:0000256|HAMAP-Rule:MF_00175,","Protease{ECO:0000313|EMBL:EGK73413.1}","Referenceproteome{ECO:0000313|Proteomes:UP000005019}","Zinc{ECO:0000256|HAMAP-Rule:MF_00175,ECO:0000256|SAAS:SAAS00645735}","Zinc-finger{ECO:0000256|HAMAP-Rule:MF_00175,"
    :param keyword:
    :return:
    """
    try:
        index_ = keyword.index("{")
    except ValueError:
        index_ = False
    if index_:
        keyword = keyword[:index_]
    return keyword.replace(".", "").strip()

def yield_entry_UniProt_dat_dump(fn_in):
    lines_list = []
    for line in tools.yield_line_uncompressed_or_gz_file(fn_in):
        line = line.strip()
        if not line.startswith("//"):
            lines_list.append(line)
        else:
            yield lines_list
            lines_list = []
    if lines_list:
        if len(lines_list[0]) == 0:
            return None
    else:
        yield lines_list

def parse_textmining_entityID_2_proteinID(fn):
    df = pd.read_csv(fn, sep="\t", names=["textmining_id", "species_id", "protein_id"])# textmining_id = entity_id
    df["ENSP"] = df["species_id"].astype(str) + "." + df["protein_id"].astype(str)
    return df

def parse_textmining_string_matches(fn):
    names=['PMID', 'sentence', 'paragraph', 'location_start', 'location_end', 'matched_string', 'species', 'entity_id']
    df = pd.read_csv(fn, sep="\t", names=names)
    return df

def Protein_2_Function_table_PMID(Protein_2_Function_table_PMID_STS_gz, Protein_2_Function_table_PMID):
    with open(Protein_2_Function_table_PMID, "w") as fh_out:
        for line in tools.yield_line_uncompressed_or_gz_file(Protein_2_Function_table_PMID_STS_gz):
            ensp, func_arr, etype = line.split("\t")
            func_arr = func_arr[1:-1].replace('"', "")
            fh_out.write("{}\t{}\t{}\n".format(ensp, func_arr, etype))

def Protein_2_Function_table_STRING(fn_list, fn_in_Taxid_2_Proteins_table_STRING, fn_out_Protein_2_Function_table_STRING, number_of_processes=1):
    fn_list = [fn for fn in fn_list]
    ### concatenate files
    fn_out_Protein_2_Function_table_STRING_temp = fn_out_Protein_2_Function_table_STRING + "_temp"
    fn_out_Protein_2_Function_table_STRING_rest = fn_out_Protein_2_Function_table_STRING + "_rest" 
    tools.concatenate_files(fn_list, fn_out_Protein_2_Function_table_STRING_temp)
    ### sort
    tools.sort_file(fn_out_Protein_2_Function_table_STRING_temp, fn_out_Protein_2_Function_table_STRING_temp, number_of_processes=number_of_processes)
    print("reduce_Protein_2_Function_table_2_STRING_proteins")
    reduce_Protein_2_Function_table_2_STRING_proteins(
        fn_in_protein_2_function_temp=fn_out_Protein_2_Function_table_STRING_temp,
        fn_in_Taxid_2_Proteins_table_STRING=fn_in_Taxid_2_Proteins_table_STRING,
        fn_out_protein_2_function_reduced=fn_out_Protein_2_Function_table_STRING,
        fn_out_protein_2_function_rest=fn_out_Protein_2_Function_table_STRING_rest,
        number_of_processes=number_of_processes)

def reduce_Protein_2_Function_table_2_STRING_proteins(fn_in_protein_2_function_temp, fn_in_Taxid_2_Proteins_table_STRING, fn_out_protein_2_function_reduced, fn_out_protein_2_function_rest, number_of_processes=1):
    """
    - reduce Protein_2_Function_table_2_STRING to relevant ENSPs (those that are in fn_in_Taxid_2_Proteins_table_STRING)
    - and remove duplicates
    second reduction step is done elsewhere (minimum number of functional associations per taxon)
    """
    ENSP_set = parse_taxid_2_proteins_get_all_ENSPs(fn_in_Taxid_2_Proteins_table_STRING)
    print('producing new file {}'.format(fn_out_protein_2_function_reduced))
    print('producing new file {}'.format(fn_out_protein_2_function_rest))
    with open(fn_in_protein_2_function_temp, "r") as fh_in:
        line_last = fh_in.readline()
        fh_in.seek(0)
        with open(fn_out_protein_2_function_reduced, "w") as fh_out_reduced:
            with open(fn_out_protein_2_function_rest, "w") as fh_out_rest:
                for line in fh_in:
                    if line_last == line:
                        continue
                    ls = line.split("\t")
                    ENSP = ls[0]
                    if ENSP in ENSP_set:
                        fh_out_reduced.write(line)
                    else:
                        fh_out_rest.write(line)
    tools.sort_file(fn_out_protein_2_function_reduced, fn_out_protein_2_function_reduced, number_of_processes=number_of_processes)
    print("finished with reduce_Protein_2_Function_table_2_STRING_proteins")

def parse_taxid_2_proteins_get_all_ENSPs(fn_Taxid_2_Proteins_table_STRING):
    ENSP_set = set()
    with open(fn_Taxid_2_Proteins_table_STRING, "r") as fh:
        for line in fh:
            taxid, num_ensps, ensp_arr  = line.strip().split("\t")
            ensp_list = ensp_arr.replace(" ", "").split(",")
            assert int(num_ensps) == len(ensp_list)
            ENSP_set |= set(ensp_list)
    return ENSP_set

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
            with open(fn_out_Function_2_ENSP_table_reduced, "w") as fh_out_reduced:
                with open(fn_out_Function_2_ENSP_table_removed, "w") as fh_out_removed:
                    for line in fh_in:
                        taxid_ENSP, taxid, etype_dont_use, function_an_set = _helper_parse_line_prot_2_func(line)
                        if not taxid in taxid_2_total_protein_count_dict.keys():
                            continue
                        if taxid != taxid_last:
                            if not taxid_last in taxid_2_total_protein_count_dict.keys():
                                taxid_last = taxid
                                continue
                            num_ENSPs_total_for_taxid = taxid_2_total_protein_count_dict[taxid_last]
                            for function_an, ENSPs in function_2_ENSPs_dict.items():
                                num_ENSPs = len(ENSPs)
                                # arr_of_ENSPs = format_list_of_string_2_postgres_array(ENSPs)
                                arr_of_ENSPs = ",".join(sorted(set(ENSPs)))
                                try:
                                    etype = function_2_etype_dict[function_an]
                                except KeyError: # for blacklisted terms in variables.py
                                    etype = "-1"
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

def Functions_table_STRING_reduced(fn_in_Functions_table, fn_in_Function_2_ENSP_table_reduced, fn_out_Functions_table_STRING_removed, fn_out_Functions_table_STRING_reduced):
    # create Functions_table_STRING_reduced
    all_relevant_functions = set()
    with open(fn_in_Function_2_ENSP_table_reduced, "r") as fh_in:
        for line in fh_in:
            function_an = line.split("\t")[2]
            all_relevant_functions.update([function_an])

    # discard all blacklisted terms from Protein_2_Function_table and Functions
    all_relevant_functions = all_relevant_functions - set(variables.blacklisted_terms)

    counter = 0
    with open(fn_out_Functions_table_STRING_reduced, "w") as fh_out_reduced:
        with open(fn_out_Functions_table_STRING_removed, "w") as fh_out_removed:
            with open(fn_in_Functions_table, "r") as fh_in:
                for line in fh_in:
                    ls = line.split("\t")
                    wrong_enum, etype, function, description, year, hier_newline = ls
                    if function in all_relevant_functions:
                        fh_out_reduced.write(str(counter) + "\t" + etype + "\t" + function + "\t" + description + "\t" + year + "\t" + hier_newline)
                        counter += 1
                    else:
                        fh_out_removed.write("-1" + "\t" + etype + "\t" + function + "\t" + description + "\t" + year + "\t" + hier_newline)

def _helper_parse_line_prot_2_func(line):        
    taxid_ENSP, function_an_set_str, etype = line.split("\t")
    taxid = taxid_ENSP.split(".")[0]
    etype = etype.strip()
    #function_an_set_str = function_an_set_str.replace('{', '')
    #function_an_set_str = function_an_set_str.replace('}', '')
    #function_an_set_str = function_an_set_str.replace('\"', '')
    function_an_set = set(function_an_set_str.replace(" ","").split(","))
    return taxid_ENSP, taxid, etype, function_an_set

def _helper_get_taxid_2_total_protein_count_dict(fn_in_Taxid_2_Proteins_table_STRING):
    taxid_2_total_protein_count_dict = {}
    with open(fn_in_Taxid_2_Proteins_table_STRING, "r") as fh_in:
        for line in fh_in:
            # taxid, ENSP_arr_str, count = line.split("\t")
            taxid, count, ENSP_arr_str = line.split("\t")
            taxid_2_total_protein_count_dict[taxid] = str(count) # count is a String not an Int (since needs to be written to file)
    return taxid_2_total_protein_count_dict

def _helper_get_function_2_funcEnum_dict__and__function_2_etype_dict(fn_in_Functions_table):
    function_2_funcEnum_dict, function_2_etype_dict = {}, {}
    with open(fn_in_Functions_table, "r") as fh_in:
        for line in fh_in:
            #print(line)
            enum, etype, an, description, year, hier_nr = line.split("\t")
            an = an.replace(" ", "")
            function_2_funcEnum_dict[an] = enum
            function_2_etype_dict[an] = etype
    return function_2_funcEnum_dict, function_2_etype_dict

def reduce_Protein_2_Function_table(fn_in_protein_2_function, fn_in_function_2_ensp_rest, fn_in_Functions_table_STRING_reduced, fn_out_protein_2_function_reduced, fn_out_protein_2_function_rest):
    """
    _by_subtracting_Function_2_ENSP_rest_and_Functions_table_STRING_reduced
    """
    # use Function_2_ENSP_table_STRING_rest to reduce Protein 2 function
    ENSP_2_assocSet_dict = {} # terms to be removed from protein_2_function
    with open(fn_in_function_2_ensp_rest, "r") as fh_in:
        for line in fh_in:
            line_split = line.strip().split("\t")
            assoc = line_split[2]
            ENSP = line_split[-1]#[2:-2]
            assert len(assoc.split(";")) == 1
            if ENSP not in ENSP_2_assocSet_dict:
                ENSP_2_assocSet_dict[ENSP] = {assoc}
            else:
                ENSP_2_assocSet_dict[ENSP] |= {assoc}

    # if functional terms not in fn_in_Functions_table_STRING_reduced then don't include in fn_out_protein_2_function_reduced
    funcs_2_include = []
    with open(fn_in_Functions_table_STRING_reduced, "r") as fh_in:
        for line in fh_in:
            funcs_2_include.append(line.split("\t")[2])
    funcs_2_include = set(funcs_2_include)

    print("producing new file {}".format(fn_out_protein_2_function_reduced))
    print("producing new file {}".format(fn_out_protein_2_function_rest))
    with open(fn_in_protein_2_function, "r") as fh_in:
        with open(fn_out_protein_2_function_reduced, "w") as fh_out_reduced:
            with open(fn_out_protein_2_function_rest, "w") as fh_out_rest:
                for line in fh_in:
                    line_split = line.strip().split("\t")
                    ENSP = line_split[0]
                    assoc_set = set(line_split[1].replace(" ", "").split(","))
                    etype = line_split[2]
                    try:
                        assoc_set_2_remove = ENSP_2_assocSet_dict[ENSP]
                        try:
                            assoc_reduced = assoc_set - assoc_set_2_remove
                            assoc_rest = assoc_set - assoc_reduced
                            assoc_reduced = [an for an in assoc_reduced if an in funcs_2_include]
                        except TypeError: # empty set, which should not happen
                            continue
                        if assoc_reduced:
                            fh_out_reduced.write(ENSP + "\t" + format_list_of_string_2_comma_separated(assoc_reduced) + "\t" + etype + "\n")
                        if assoc_rest:
                            fh_out_rest.write(ENSP + "\t" + format_list_of_string_2_comma_separated(assoc_rest) + "\t" + etype + "\n")
                    except KeyError:
                        assoc_reduced, assoc_rest = [], []
                        for an in assoc_set:
                            if an in funcs_2_include:
                                assoc_reduced.append(an)
                            else:
                                assoc_rest.append(an)
                        if assoc_reduced:
                            fh_out_reduced.write(ENSP + "\t" + format_list_of_string_2_comma_separated(assoc_reduced) + "\t" + etype + "\n")
                        if assoc_rest:
                            fh_out_rest.write(ENSP + "\t" + format_list_of_string_2_comma_separated(assoc_rest) + "\t" + etype + "\n")
    print("finished with reduce_Protein_2_Function_by_subtracting_Function_2_ENSP_rest")

def AFC_KS_enrichment_terms_flat_files(functions_table, protein_shorthands, KEGG_TaxID_2_acronym_table, Function_2_ENSP_table_STRING, GO_obo_Jensenlab, GO_basic_obo, UPK_obo, RCTM_hierarchy, interpro_parent_2_child_tree, tree_STRING_clusters, DOID_obo_Jensenlab, BTO_obo_Jensenlab,  global_enrichment_data_current_tar_gz, populate_classification_schema_current_sql_gz):
    print("creating AFC_KS files")
    global_enrichment_data_DIR = variables.tables_dict["global_enrichment_data_DIR"]
    year_arr, hierlevel_arr, entitytype_arr, functionalterm_arr, indices_arr, description_arr, category_arr = get_lookup_arrays(functions_table, low_memory=False)
    functionalterm_set = set(functionalterm_arr)
    term_2_enum_dict = {key: val for key, val in zip(functionalterm_arr, indices_arr)}
    # term_2_description_dict = {key: val for key, val in zip(functionalterm_arr, description_arr)}
    ENSP_2_internalID_dict = {}
    with open(protein_shorthands, "r") as fh:
        for line in fh:
            ENSP, internalID = line.split()
            ENSP_2_internalID_dict[ENSP] = internalID.strip()
    taxid_2_acronym_dict = {}
    with open(KEGG_TaxID_2_acronym_table, "r") as fh:
        for line in fh:
            taxid, acronym = line.split("\t")
            acronym = acronym.strip()
            taxid_2_acronym_dict[taxid] = acronym

    parent_2_child_dict = get_parent_2_direct_children_dict(GO_obo_Jensenlab, GO_basic_obo, UPK_obo, RCTM_hierarchy, interpro_parent_2_child_tree, tree_STRING_clusters, DOID_obo_Jensenlab, BTO_obo_Jensenlab)
    parent_2_child_dict_ENUM, term_without_enum_list = {}, []
    for parent, child_list in parent_2_child_dict.items():
        try:
            parent_enum = term_2_enum_dict[parent]
        except KeyError:
            term_without_enum_list.append(parent)
            parent_enum = -1
        child_enum_list = []
        for child in child_list:
            try:
                child_enum = term_2_enum_dict[child]
            except KeyError:
                term_without_enum_list.append(child)
                # child_enum = -1
                continue
            child_enum_list.append(child_enum)
        parent_2_child_dict_ENUM[parent_enum] = sorted(child_enum_list)
    # len(parent_2_child_dict_ENUM), len(parent_2_child_dict)

    psql_intermittent_chars = "\.\n"

    psql_1 = """CREATE TABLE classification.terms_proteins_temp (
    \tterm_id integer,
    \tspecies_id integer,
    \tprotein_id integer
    ) WITHOUT OIDS;
    CREATE TABLE classification.terms_counts_temp (
    \tterm_id integer,
    \tspecies_id integer,
    \tmember_count integer
    ) WITHOUT OIDS;
    CREATE TABLE classification.terms_temp (
    \tterm_id integer,
    \tterm_external_id_full character varying (100),
    \tterm_external_id_compact character varying (100),
    \tdescription character varying
    ) WITHOUT OIDS;
    COPY classification.terms_proteins_temp FROM stdin;\n"""

    # table_1
    # psql_intermittent_chars

    psql_2 = "COPY classification.terms_counts_temp FROM stdin;\n"
    # table_2
    # psql_intermittent_chars

    psql_3 = "COPY classification.terms_temp FROM stdin;\n"
    # table_3
    # psql_intermittent_chars

    psql_4 = """CREATE INDEX pi_terms_term_id_temp ON classification.terms_temp (term_id);
    CREATE INDEX si_terms_term_external_id_temp ON classification.terms_temp (term_external_id_full);
    CLUSTER pi_terms_term_id_temp ON classification.terms_temp;
    VACUUM ANALYZE classification.terms_temp;

    CREATE INDEX pi_terms_proteins_term_id_species_id_temp ON classification.terms_proteins_temp (term_id, species_id);
    CLUSTER pi_terms_proteins_term_id_species_id_temp ON classification.terms_proteins_temp;
    VACUUM ANALYZE classification.terms_proteins_temp;

    CREATE INDEX pi_terms_counts_term_id_species_id_temp ON classification.terms_counts_temp (term_id, species_id);
    CLUSTER pi_terms_counts_term_id_species_id_temp ON classification.terms_counts_temp;
    VACUUM ANALYZE classification.terms_counts_temp;"""

    ### table_1 terms_proteins_temp  # sort order: termEnum, taxid, NOT proteinEnum but ENSP  # termEnum, taxid, proteinEnum
    ### table_2 terms_counts_temp  # sort order: termEnum, taxon  # termEnum, taxid, num_of_proteins
    ### table_3 terms_temp  # sort order: termEnum  # termEnum, term, compact_term, description  # ?compact_term? -->1577887:CL:105  CL:105

    ### df with 4 columns, but printing only 3
    ### termEnum, taxid, proteinEnum, ENSP
    ### sort_values(["termEnum", "taxid", "ENSP"])
    ### df["termEnum", "taxid", "proteinEnum"]
    termEnum_l, taxid_l, proteinEnum_l, ENSP_l, etype_l = [], [], [], [], []
    term_without_description_list, ENSP_without_protEnum_list, term_without_enum_list = [], [], []
    with open(Function_2_ENSP_table_STRING, "r") as fh_in:
        for line in fh_in:
            taxid, etype, term, background_count, background_n, an_array = line.split()
            taxid = int(taxid)
            etype = int(etype)
            # ENSP_list = an_array.strip()[1:-1].replace('"', "").split(",")
            ENSP_list = an_array.strip().replace(" ", "").split(",")
            if term not in functionalterm_set:
                continue
            try:
                termEnum = term_2_enum_dict[term]
            except KeyError:
                term_without_enum_list.append(term)
                continue
            num_ENSPs = len(ENSP_list)
            taxid_l += [taxid] * num_ENSPs
            termEnum_l += [termEnum] * num_ENSPs
            ENSP_list = sorted(ENSP_list)
            ENSP_l += ENSP_list
            etype_l += [etype] * num_ENSPs
            proteinEnum_list = []
            for ENSP in ENSP_list:
                try:
                    protEnum = ENSP_2_internalID_dict[ENSP]
                except KeyError:
                    ENSP_without_protEnum_list.append(ENSP)
                    protEnum = -1
                proteinEnum_list.append(protEnum)
            proteinEnum_l += proteinEnum_list  # don't sort!! (should be sorted according to ProtName not ProtEnum)

    df = pd.DataFrame()
    df["termEnum"] = termEnum_l
    df["taxid"] = taxid_l
    df["proteinEnum"] = proteinEnum_l
    df["ENSP"] = ENSP_l
    df["etype"] = etype_l
    print(df.shape)
    df = df.drop_duplicates()
    print(df.shape)
    df = df.sort_values(["termEnum", "taxid", "ENSP"], ascending=[True, True, True]).reset_index(drop=True)
    # table_1 = df[["termEnum", "taxid", "proteinEnum"]].to_csv(header=False, index=False, sep='\t')

    ### table_2 terms_counts_temp
    ### sort order: termEnum, taxon
    ### termEnum, taxid, num_of_proteins
    df_table2 = df[["termEnum", "taxid", "proteinEnum"]].groupby(["termEnum", "taxid"]).size().reset_index(name="num_proteins").sort_values(["termEnum", "taxid", "num_proteins"]).reset_index(drop=True)
    # table_2 = df_table2.to_csv(header=False, index=False, sep='\t')

    ### table_3 terms_temp --> preloads
    ### sort order: termEnum
    ### termEnum, term, compact_term, description
    ### ?compact_term? --> 1577887:CL:105  CL:105
    df_table3 = pd.DataFrame()
    df_table3["termEnum"] = indices_arr
    df_table3["term"] = functionalterm_arr
    df_table3["description"] = description_arr
    df_table3["etype"] = entitytype_arr
    cond = df_table3["etype"] == -78 # STRING_clusters
    df_table3["compact_term"] = df_table3["term"]
    df_table3.loc[cond, "compact_term"] = df_table3.loc[cond, "compact_term"].apply(lambda x: x.split("_")[1])
    df_table3.loc[cond, "term"] = df_table3.loc[cond, "term"].apply(lambda x: ":".join(x.split("_")))
    # table_3 = df_table3[["termEnum", "term", "compact_term", "description"]].to_csv(header=False, index=False, sep='\t')
    print("writing sql file")
    # fn_out_sql_temp = populate_classification_schema_current_sql_gz + "_temp"
    # with open(fn_out_sql_temp, "w") as fh_out_sql:
    with gzip.open(populate_classification_schema_current_sql_gz, "wt") as fh_out_sql:
        fh_out_sql.write(psql_1)
        fh_out_sql.write(df[["termEnum", "taxid", "proteinEnum"]].to_csv(header=False, index=False, sep='\t'))
        fh_out_sql.write(psql_intermittent_chars)
        fh_out_sql.write(psql_2)
        fh_out_sql.write(df_table2.to_csv(header=False, index=False, sep='\t'))
        fh_out_sql.write(psql_intermittent_chars)
        fh_out_sql.write(psql_3)
        fh_out_sql.write(df_table3[["termEnum", "term", "compact_term", "description"]].to_csv(header=False, index=False, sep='\t'))
        fh_out_sql.write(psql_intermittent_chars)
        fh_out_sql.write(psql_4)
    # subprocess.call("gzip -c {} > {}".format(fn_out_sql_temp, populate_classification_schema_current_sql_gz), shell=True)
    # process_gzip = subprocess.Popen(split("gzip -c {} > {}".format(fn_out_sql_temp, populate_classification_schema_current_sql_gz)))

    print("writing 3 files per taxid: members, descriptions, and children")
    termEnum_without_lineage_list = []
    ### create taxid.terms_members.tsv and taxid.terms_descriptions.tsv
    if not os.path.exists(global_enrichment_data_DIR):
        os.makedirs(global_enrichment_data_DIR)
    for taxid, df_taxid in df.groupby("taxid"):
        fn_out_members = os.path.join(global_enrichment_data_DIR, "{}.terms_members.tsv".format(taxid))
        fn_out_descriptions = os.path.join(global_enrichment_data_DIR, "{}.terms_descriptions.tsv".format(taxid))
        fn_out_children = os.path.join(global_enrichment_data_DIR, "{}.terms_children.tsv".format(taxid))
        with open(fn_out_members, "w") as fh_out_members:
            for termEnum, df_termEnum in df_taxid.groupby("termEnum"):
                etype = df_termEnum["etype"].iloc[0]
                ENSP_list = df_termEnum["ENSP"].to_list()
                protein_shorthands_list = " ".join(sorted(map_ENSPs_2_internalIDs(ENSP_list, ENSP_2_internalID_dict)))
                number_of_proteins = len(ENSP_list)
                fh_out_members.write("{}\t{}\t{}\t{}\n".format(termEnum, etype, number_of_proteins, protein_shorthands_list))

        termEnum_arr_for_taxid = df_taxid["termEnum"].values
        try:  # KEGG is "map" and needs to be translated to e.g. "hsa" instead
            acronym = taxid_2_acronym_dict[str(taxid)]
        except KeyError:
            acronym = "map"
        with open(fn_out_descriptions, "w") as fh_out_descriptions:
            cond_taxid = df_table3["termEnum"].isin(termEnum_arr_for_taxid)
            # here we want "hsa00010" and not "map00010" --> for KEGG etype -52
            df_temp = df_table3.loc[cond_taxid, ["termEnum", "term", "description", "etype"]]
            if acronym != "map":
                cond_KEGG = df_temp["etype"] == -52
                df_temp.loc[cond_KEGG, "term"] = df_temp.loc[cond_KEGG, "term"].apply(lambda x: x.replace("map", acronym))
            fh_out_descriptions.write(df_temp[["termEnum", "term", "description"]].to_csv(header=False, index=False, sep='\t'))

        with open(fn_out_children, "w") as fh_out_children:
            for termEnum in sorted(set(termEnum_arr_for_taxid)):
                try:
                    childEnum_list = parent_2_child_dict_ENUM[termEnum]
                except KeyError:
                    termEnum_without_lineage_list.append(termEnum)
                    # childEnum_list = [-1]
                    continue
                number_of_children = len(childEnum_list)
                if number_of_children > 0:
                    fh_out_children.write("{}\t{}\t{}\n".format(termEnum, number_of_children, "\t".join(str(ele) for ele in childEnum_list)))
    # tar -czf "$global_enrichment_data_current"./global_enrichment_data
    print("creating tar.gz")
    # process_tar_gz = subprocess.Popen(split("tar -czf {} {}".format(global_enrichment_data_current_tar_gz, global_enrichment_data_DIR)))
    process_tar_gz = subprocess.Popen(split("tar -czf {} -C {} {}".format(global_enrichment_data_current_tar_gz, os.path.dirname(global_enrichment_data_DIR), os.path.basename(global_enrichment_data_DIR))))
    code_tar_gz = process_tar_gz.wait()
    # code_gzip = process_gzip.wait()
    # os.remove(fn_out_sql_temp)
    print("finished AFC KS global enrichment  :)")

def AFC_KS_enrichment_terms_flat_files_v0(fn_in_Protein_shorthands, fn_in_Functions_table_STRING_reduced, fn_in_Function_2_ENSP_table_STRING_reduced, KEGG_TaxID_2_acronym_table, fn_GO_obo_Jensenlab, fn_go_basic_obo, fn_keywords_obo, fn_rctm_hierarchy, fn_in_interpro_parent_2_child_tree, fn_tree_STRING_clusters, fn_DOID_obo_Jensenlab, fn_BTO_obo_Jensenlab, fn_out_AFC_KS_DIR, verbose=True):
    parent_2_direct_children_dict = get_parent_2_direct_children_dict(fn_GO_obo_Jensenlab, fn_go_basic_obo, fn_keywords_obo, fn_rctm_hierarchy, fn_in_interpro_parent_2_child_tree, fn_tree_STRING_clusters, fn_DOID_obo_Jensenlab, fn_BTO_obo_Jensenlab)

    print("AFC_KS_enrichment_terms_flat_files start")
    ENSP_2_internalID_dict = {}
    with open(fn_in_Protein_shorthands, "r") as fh:
        for line in fh:
            ENSP, internalID = line.split()
            internalID = internalID.strip()
            ENSP_2_internalID_dict[ENSP] = internalID

    association_2_description_dict = {}
    with open(fn_in_Functions_table_STRING_reduced, "r") as fh:
        for line in fh:
            enum, etype, an, description, year, level = line.split("\t")
            association_2_description_dict[an] = description

    taxid_2_acronym_dict = {}
    with open(KEGG_TaxID_2_acronym_table, "r") as fh:
        for line in fh:
            taxid, acronym = line.split("\t")
            acronym = acronym.strip()
            taxid_2_acronym_dict[taxid] = acronym
    fn_out_prefix = os.path.join(fn_out_AFC_KS_DIR + "/{}_AFC_KS_all_terms.tsv")
    with open(fn_in_Function_2_ENSP_table_STRING_reduced, "r") as fh_in:
        taxid_last, etype, association, background_count, background_n, an_array = fh_in.readline().split()
        fn_out = fn_out_prefix.format(taxid_last)
        fn_out_lineage = fn_out.replace(".tsv", "_lineage.tsv")
        if not os.path.exists(fn_out_AFC_KS_DIR):
            os.makedirs(fn_out_AFC_KS_DIR)
        fh_out = open(fn_out, "w")
        fh_out_lineage = open(fn_out_lineage, "w")
        fh_in.seek(0)
        for line in fh_in:
            taxid, etype, association, background_count, background_n, an_array = line.split()
            an_array_list = an_array.replace(" ", "").split(",")
            an_array = []
            for an in an_array_list:
                an_array.append(an)
            an_array = "{" + str(sorted(set(an_array)))[1:-1].replace(" ", "").replace("'", '"') + "}"
            an_array = literal_eval(an_array)
            try:
                description = association_2_description_dict[association]
            except KeyError: # since removed due to e.g. blacklisting
                continue
            number_of_ENSPs = str(len(an_array))
            array_of_ENSPs_with_internal_IDS = " ".join(sorted(map_ENSPs_2_internalIDs(an_array, ENSP_2_internalID_dict)))
            if taxid != taxid_last:
                fh_out.close()
                fh_out_lineage.close()
                fn_out = fn_out_prefix.format(taxid)
                fn_out_lineage = fn_out.replace(".tsv", "_lineage.tsv")
                fh_out = open(fn_out, "w")
                fh_out_lineage = open(fn_out_lineage, "w")
            if etype == "-52": # KEGG
                try:
                    acronym = taxid_2_acronym_dict[taxid]
                except KeyError:
                    # print("no KEGG acronym translation for TaxID: {}".format(taxid))
                    acronym = "map"
                association = association.replace("map", acronym)
            fh_out.write(association + "\t" + etype + "\t" + description + "\t" + number_of_ENSPs + "\t" + array_of_ENSPs_with_internal_IDS + "\n")
            taxid_last = taxid
            try:
                children_list = parent_2_direct_children_dict[association]
            except KeyError:
                continue
            fh_out_lineage.write(association + "\t" + "\t".join(children_list) + "\n")
        fh_out.close()
        fh_out_lineage.close()
    print("AFC_KS_enrichment_terms_flat_files done :)")

def map_ENSPs_2_internalIDs(ENSPs, ENSP_2_internalID_dict):
    list_2_return = []
    for ENSP in ENSPs:
        try:
            internalID = ENSP_2_internalID_dict[ENSP]
            list_2_return.append(internalID)
        except KeyError:
            pass
            #print("{} # no internal ID found".format(ENSP))
    return list_2_return

def Functions_table_PMID_cleanup(Functions_table_PMID_all, max_len_description, Functions_table_PMID):
    """
    make Lars download file conform to overall Functions_table style
    hierarchy "-1" missing, year without info is "()" but should be "(....)"
    before:
    -56     PMID:26516301   () Mining the Breast Cancer Proteome for Predictors of Drug Sensitivity.
    -56     PMID:20534597   (2010) Circulating microRNAs are blabla of myocardial infarction.         2010
    after:
    -56     PMID:26516301   (....) Mining the Breast Cancer Proteome for Predictors of Drug Sensitivity.    ....    -1
    """
    hierarchy = "-1\n"
    max_len_description = int(max_len_description) # since can be passed as string by Snakemake
    tags_2_remove = re.compile("|".join([r"<[^>]+>", r"\[Purpose\]", r"\\", "\/"]))
    with open(Functions_table_PMID, "w") as fh_out:
        for line in tools.yield_line_uncompressed_or_gz_file(Functions_table_PMID_all):
            ls = line.split("\t")
            etype, pmid, description, year = ls
            year = year.strip()
            if not year: # is an empty string
                year = "-1"
                description = "(....)" + description[2:]
            else:
                pass
            description = helper_clean_messy_string(description) # in order to capture foreign language titles' open and closing brackets e.g. "[bla bla bla]"
            description = helper_cut_long_string_at_word(description, max_len_description)
            description = tags_2_remove.sub('', description)
            fh_out.write("{}\t{}\t{}\t{}\t{}".format(etype, pmid, description, year, hierarchy))

def helper_cut_long_string_at_word(string_, max_len_description):
    if len(string_) > max_len_description:
        string_2_use = ""
        for word in string_.split(" "):
            if len(string_2_use + word) > max_len_description:
                string_2_return = string_2_use.strip() + " ..."
                assert len(string_2_return) <= (max_len_description + 4)
                return string_2_return
            else:
                string_2_use += word + " "
    else:
        return string_.strip()

def helper_clean_messy_string(string_):
    string_ = string_.strip().replace('"', "'")
    tags_2_remove = re.compile("|".join([r"<[^>]+>", r"\[Purpose\]", r"\\", "\/"]))
    string_ = tags_2_remove.sub('', string_)
    if string_.startswith("[") and string_.endswith("]"):
        return helper_clean_messy_string(string_[1:-1])
    elif string_.startswith("[") and string_.endswith("]."):
        return helper_clean_messy_string(string_[1:-2])
    elif string_.isupper():
        return string_[0] + string_[1:].lower()
    else:
        return string_

def add_2_DF_file_dimensions_log(LOG_DF_FILE_DIMENSIONS, LOG_DF_FILE_DIMENSIONS_GLOBAL_ENRICHMENT, global_enrichment_data_current_tar_gz, populate_classification_schema_current_sql_gz, Taxid_2_FunctionCountArray_table_STRING):
    """
    read old log and add number of lines of flat files and bytes of data for binary files to log,
    write to disk
    :return: None
    """
    # assert os.path.exists(taxid_2_proteome_count_dict)
    assert os.path.exists(global_enrichment_data_current_tar_gz)
    assert os.path.exists(populate_classification_schema_current_sql_gz)
    assert os.path.exists(Taxid_2_FunctionCountArray_table_STRING)

    # read old table and add data to it
    df_old = pd.read_csv(LOG_DF_FILE_DIMENSIONS, sep="\t")

    fn_list, binary_list, size_list, num_lines_list, date_list, checksum_list = [], [], [], [], [], []
    for fn in sorted(os.listdir(TABLES_DIR)):
        fn_abs_path = os.path.join(TABLES_DIR, fn)
        if fn.endswith("STS_FIN.txt"): ## not needed since only static file from STRING_v11 kegg_taxid_2_acronym_table_STS_FIN.txt
            binary_list.append(False)
            num_lines_list.append(tools.line_numbers(fn_abs_path))
        # if fn.endswith("STS_FIN.p"):
        #     binary_list.append(True)
        #     num_lines_list.append(np.nan)
        else:
            continue
        fn_list.append(fn)
        size_list.append(os.path.getsize(fn_abs_path))
        timestamp = tools.creation_date(fn_abs_path)
        date_list.append(datetime.datetime.fromtimestamp(timestamp))
        checksum_list.append(tools.md5(fn_abs_path))

    df = pd.DataFrame()
    df["fn"] = fn_list
    df["binary"] = binary_list
    df["size"] = size_list
    df["num_lines"] = num_lines_list
    df["date"] = date_list
    # df["version"] = max(df_old["version"]) + 1
    try:
        version = max(df_old["version"])
    except ValueError:
        version = 0
    df["version"] = version + 1
    df["checksum"] = checksum_list
    df = pd.concat([df_old, df])
    df.to_csv(LOG_DF_FILE_DIMENSIONS, sep="\t", header=True, index=False)

    ### Global enrichment follows
    df_old = pd.read_csv(LOG_DF_FILE_DIMENSIONS_GLOBAL_ENRICHMENT, sep="\t")
    populate_classification_schema_current_sql_gz = variables.tables_dict["populate_classification_schema_current_sql_gz"]
    global_enrichment_data_current_tar_gz = variables.tables_dict["global_enrichment_data_current_tar_gz"]
    global_enrichment_data_DIR = variables.tables_dict["global_enrichment_data_DIR"]
    fn_list_2_search = [populate_classification_schema_current_sql_gz, global_enrichment_data_current_tar_gz]
    fn_list_2_search += [os.path.join(global_enrichment_data_DIR, fn) for fn in os.listdir(global_enrichment_data_DIR)]

    fn_list, binary_list, size_list, num_lines_list, date_list, md5_list = [], [], [], [], [], []
    for fn in fn_list_2_search:
        if fn.endswith("global_enrichment_data_current.tar.gz") or fn.endswith("populate_classification_schema_current.sql.gz"):
            binary_list.append(True)
            num_lines_list.append(np.nan)
        elif fn.endswith(".terms_members.tsv") or fn.endswith(".terms_descriptions.tsv") or fn.endswith(".terms_children.tsv"):
            binary_list.append(False)
            num_lines_list.append(tools.line_numbers(fn))
        else:
            continue
        size_list.append(os.path.getsize(fn))
        timestamp = os.path.getmtime(fn)
        date_list.append(datetime.datetime.fromtimestamp(timestamp))
        md5_list.append(tools.md5(fn))
        fn_list.append(os.path.basename(fn))
    df = pd.DataFrame()
    df["fn"] = fn_list
    df["binary"] = binary_list
    df["size"] = size_list
    df["num_lines"] = num_lines_list
    df["date"] = date_list
    df["md5"] = md5_list
    try:
        version = max(df_old["version"])
    except ValueError:
        version = 0
    df["version"] = version + 1
    df = pd.concat([df_old, df])
    df.to_csv(LOG_DF_FILE_DIMENSIONS_GLOBAL_ENRICHMENT, sep="\t", header=True, index=False)

def get_EntrezGeneID_2_ENSP(fn):
    """
    taxid   entrez  ENSP
    1217658 23003381        1217658.F987_00645
    1217658 23003382        1217658.F987_00644
    """
    df = pd.read_csv(fn, sep='\t')
    EntrezGeneID_2_ENSP_dict = {entrez: [ENSP] for entrez, ENSP in zip(df["entrez"], df["ENSP"])}
    return EntrezGeneID_2_ENSP_dict

def Protein_2_Function__and__Functions_table_WikiPathways_STS(fn_in_WikiPathways_organisms_metadata, fn_in_STRING_EntrezGeneID_2_STRING, Human_WikiPathways_gmt, fn_out_Functions_table_WikiPathways, fn_out_Protein_2_Function_table_WikiPathways, verbose=True): # fn_in_STRING_EntrezGeneID_2_STRING, fn_in_Taxid_2_Proteins_table_STS
    """
    DOWNLOADS_DIR = "/home/dblyon/agotool_PMID_autoupdate/agotool/data/PostgreSQL/downloads"
    TABLES_DIR = "/home/dblyon/agotool_PMID_autoupdate/agotool/data/PostgreSQL/tables"
    WikiPathways_organisms_metadata = os.path.join(DOWNLOADS_DIR, "WikiPathways_organisms_metadata.tsv") # ancient
    STRING_EntrezGeneID_2_STRING = os.path.join(DOWNLOADS_DIR, "STRING_v11_all_organisms_entrez_2_string_2018.tsv")
    Human_WikiPathways_gmt = r"/scratch/dblyon/agotool/data/PostgreSQL/downloads/wikipathways-Homo_sapiens.gmt"
    Functions_table_WikiPathways = os.path.join(TABLES_DIR, "Functions_table_WikiPathways.txt")
    Protein_2_Function_table_WikiPathways_STS = os.path.join(TABLES_DIR, "Protein_2_Function_table_WikiPathways_STS.txt")
    Protein_2_Function__and__Functions_table_WikiPathways_STS(WikiPathways_organisms_metadata, STRING_EntrezGeneID_2_STRING, Human_WikiPathways_gmt, Functions_table_WikiPathways, Protein_2_Function_table_WikiPathways_STS)

    link http://data.wikipathways.org
    use gmt = Gene Matrix Transposed, lists of datanodes per pathway, unified to Entrez Gene identifiers.
    map Entrez Gene IDs to UniProt using ftp://ftp.expasy.org/databases/uniprot/current_release/knowledgebase/idmapping/idmapping_selected.tab.gz
    """
    if verbose:
        print("creating Functions_table_WikiPathways and Protein_2_Function_table_WikiPathways")
    df_wiki_meta = pd.read_csv(fn_in_WikiPathways_organisms_metadata, sep="\t")
    df_wiki_meta["Genus species"] = df_wiki_meta["Genus species"].apply(lambda s: "_".join(s.split(" ")))
    TaxName_2_Taxid_dict = pd.Series(df_wiki_meta["Taxid"].values, index=df_wiki_meta["Genus species"]).to_dict()
    year, level = "-1", "-1"
    etype = "-58"
    EntrezGeneID_2_ENSP_dict = get_EntrezGeneID_2_ENSP(fn_in_STRING_EntrezGeneID_2_STRING) # previously fn_in_UniProt_ID_mapping
    WikiPathways_dir = os.path.dirname(Human_WikiPathways_gmt)
    fn_list = [os.path.join(WikiPathways_dir, fn) for fn in os.listdir(WikiPathways_dir) if fn.endswith(".gmt")]
    already_written = []
    with open(fn_out_Functions_table_WikiPathways, "w") as fh_out_functions:  # etype | an | description | year | level
        with open(fn_out_Protein_2_Function_table_WikiPathways, "w") as fh_out_protein_2_function:  # an | func_array | etype
            for fn_wiki in fn_list:
                taxname = fn_wiki.split("-")[-1].replace(".gmt", "")
                try:
                    taxid = TaxName_2_Taxid_dict[taxname]  # taxid is an integer
                except KeyError:
                    print("WikiPathways, couldn't translate TaxName from file: {}".format(fn_wiki))
                    continue
                with open(fn_wiki, "r") as fh_in: # remove dupliates
                    # remember pathway to proteins mapping --> then translate to ENSP to func_array
                    WikiPathwayID_2_EntrezGeneIDList_dict = {}
                    for line in fh_in:  # DNA Replication%WikiPathways_20190310%WP1223%Anopheles gambiae	http://www.wikipathways.org/instance/WP1223_r68760	1275918	1275917	1282031	3290537	1276035	1280711	1281887
                        pathwayName_version_pathwayID_TaxName, url_, *entrez_ids = line.strip().split("\t")  # 'DNA Replication', 'WikiPathways_20190310', 'WP1223', 'Anopheles gambiae', ['1275918', ... ]
                        pathwayName, version, pathwayID, TaxName = pathwayName_version_pathwayID_TaxName.split("%")
                        description = pathwayName
                        an = pathwayID
                        WikiPathwayID_2_EntrezGeneIDList_dict[pathwayID] = entrez_ids
                        line_2_write = etype + "\t" + an + "\t" + description + "\t" + year + "\t" + level + "\n"
                        if line_2_write not in already_written:
                            fh_out_functions.write(line_2_write) # check for uniqueness of names/ IDs later
                            already_written.append(line_2_write)

                    # map to UniProt and to STRING, single pathway to multiple entrez_ids translate to ENSP/UniProtAN to multiple pathways
                    ENSP_2_wiki_dict = {}
                    for WikiPathwayID, EntrezGeneID_list in WikiPathwayID_2_EntrezGeneIDList_dict.items():
                        for EntrezGeneID in EntrezGeneID_list:
                            try:
                                ENSP_list = EntrezGeneID_2_ENSP_dict[EntrezGeneID]
                            except KeyError:
                                ENSP_list = []
                            for ENSP in ENSP_list:
                                if ENSP not in ENSP_2_wiki_dict:
                                    ENSP_2_wiki_dict[ENSP] = [WikiPathwayID]
                                else:
                                    ENSP_2_wiki_dict[ENSP].append(WikiPathwayID)
                    for ENSP, wiki_list in ENSP_2_wiki_dict.items():
                        func_array = ",".join(sorted(set(wiki_list)))
                        fh_out_protein_2_function.write( ENSP + "\t" + "{" + func_array + "}" + "\t" + etype + "\n")  # str(taxid) + "\t" +

if __name__ == "__main__":
    pass

def Functions_table_RCTM(fn_in_descriptions, fn_in_hierarchy, fn_out_Functions_table_RCTM, all_terms=None):
    """
    entity_type = "-57"
    :param fn_in_descriptions: String (RCTM_descriptions.tsv)
    :param fn_in_hierarchy: String
    :param fn_out_Functions_table_RCTM: String (Function_table_RCTM.txt)
    :param all_terms: Set of String (with all RCTM terms that have any association with the given ENSPs)
    :return: Tuple (List of terms with hierarchy, Set of terms without hierarchy)
    do a sanity check: are terms without a hierarchy used in protein_2_function
    create file Functions_table_Reactome.txt
    etype, term, name, definition, description # old
    | enum | etype | an | description | year | level | # new
    """
    child_2_parent_dict = get_child_2_direct_parent_dict_RCTM(fn_in_hierarchy)  # child_2_parent_dict --> child 2 direct parents
    term_2_level_dict = get_term_2_level_dict(child_2_parent_dict)
    entity_type = variables.id_2_entityTypeNumber_dict["Reactome"]
    year = "-1"
    terms_with_hierarchy, terms_without_hierarchy = [], []
    with open(fn_in_descriptions, "r") as fh_in:
        with open(fn_out_Functions_table_RCTM, "w") as fh_out:
            for line in fh_in:
                term, description, taxname = line.split("\t")
                if term.startswith("R-"):  # R-ATH-109581 --> ATH-109581
                    term = term[2:]
                description = description.strip()
                try:
                    level = term_2_level_dict[term]
                    terms_with_hierarchy.append(term)
                except KeyError:
                    terms_without_hierarchy.append(term)
                    level = "-1"
                if all_terms is None:
                    fh_out.write(entity_type + "\t" + term + "\t" + description + "\t" + year + "\t" + str(level) + "\n")
                else:
                    if term in all_terms:  # filter relevant terms that occur in protein_2_functions_tables_RCTM.txt
                        fh_out.write(entity_type + "\t" + term + "\t" + description + "\t" + year + "\t" + str(level) + "\n")
    return sorted(set(terms_with_hierarchy)), sorted(set(terms_without_hierarchy))

def Functions_table_DOID_BTO_GOCC(Function_2_Description_DOID_BTO_GO_down, BTO_obo_Jensenlab, DOID_obo_Jensenlab, GO_obo_Jensenlab, Blacklisted_terms_Jensenlab, Functions_table_DOID_BTO_GOCC, GO_CC_textmining_additional_etype=True, number_of_processes=4, verbose=True):
    """
    - add hierarchical level, year placeholder
    - merge with Functions_table
    | enum | etype | an | description | year | level |
    """
    # get term 2 hierarchical level
    bto_dag = obo_parser.GODag(obo_file=BTO_obo_Jensenlab)
    child_2_parent_dict = get_child_2_direct_parent_dict_from_dag(bto_dag)  # obsolete or top level terms have empty set for parents
    term_2_level_dict_bto = get_term_2_level_dict(child_2_parent_dict)
    doid_dag = obo_parser.GODag(obo_file=DOID_obo_Jensenlab)
    child_2_parent_dict = get_child_2_direct_parent_dict_from_dag(doid_dag)  # obsolete or top level terms have empty set for parents
    term_2_level_dict_doid = get_term_2_level_dict(child_2_parent_dict)

    gocc_dag = obo_parser.GODag(obo_file=GO_obo_Jensenlab)
    child_2_parent_dict = get_child_2_direct_parent_dict_from_dag(gocc_dag)  # obsolete or top level terms have empty set for parents
    term_2_level_dict_gocc_temp = get_term_2_level_dict(child_2_parent_dict)
    term_2_level_dict_gocc = {}
    # convert "GO:" to "GOCC:"
    for term, level in term_2_level_dict_gocc_temp.items():
        term = term.replace("GO:", "GOCC:")
        term_2_level_dict_gocc[term] = level

    term_2_level_dict = {}
    term_2_level_dict.update(term_2_level_dict_doid)
    term_2_level_dict.update(term_2_level_dict_bto)
    term_2_level_dict.update(term_2_level_dict_gocc)
    # get blacklisted terms to exclude them
    blacklisted_ans = []
    with open(Blacklisted_terms_Jensenlab, "r") as fh:
        for line in fh:
            etype, an = line.split("\t")
            # don't include Lars' blacklisted GO terms
            # Lars' blacklist is for a subcellular localization resource, so telling that the protein is part of complex X is not
            # really the information that you are after. But for the enrichment, the situation is different.
            if etype != "-22":
                blacklisted_ans.append(an.strip())
    blacklisted_ans = set(blacklisted_ans)
    blacklisted_ans.update(variables.blacklisted_terms) # exclude top level terms, and manually curated

    year = "-1" # placeholder
    with open(Functions_table_DOID_BTO_GOCC, "w") as fh_out:
        for line in tools.yield_line_uncompressed_or_gz_file(Function_2_Description_DOID_BTO_GO_down):
            etype, function_an, description = line.split("\t")
            if GO_CC_textmining_additional_etype:
                if etype == "-22":
                    etype = "-20"
                    function_an = function_an.replace("GO:", "GOCC:")
            description = description.strip()
            if function_an in blacklisted_ans:
                continue
            try:
                level = term_2_level_dict[function_an] # level is an integer
            except KeyError:
                level = -1
            fh_out.write(etype + "\t" + function_an + "\t" + description + "\t" + year + "\t" + str(level) + "\n")

    # remove redundant terms, keep those with "better" descriptions (not simply GO-ID as description e.g.
    # -22     GO:0000793      Condensed chromosome
    # -22     GO:0000793      GO:0000793
    # sort it
    # remove redundant terms
    # overwrite redundant file with cleaned up version
    '''tools.sort_file(Functions_table_DOID_BTO_GOCC, Functions_table_DOID_BTO_GOCC, number_of_processes=number_of_processes, verbose=verbose)
    func_redundancy_dict = {}
    Functions_table_DOID_BTO_GOCC_temp = Functions_table_DOID_BTO_GOCC + "_temp"
    with open(Functions_table_DOID_BTO_GOCC_temp, "w") as fh_out:
        with open(Functions_table_DOID_BTO_GOCC, "r") as fh_in:
            line = next(fh_in)
            etype_last, function_last, description_last, year_last, hier_last = line.split("\t")
            func_redundancy_dict[function_last] = line
            for line in fh_in:
                etype, function, description, year, hier = line.split("\t")
                if function in func_redundancy_dict:
                    # take every description, but overwrite existing only if function_id is not equal to description
                    if function.replace("GOCC:", "GO:").strip().lower() != description.strip().lower():
                        func_redundancy_dict[function] = line
                else:
                    func_redundancy_dict[function] = line
        for line in sorted(func_redundancy_dict.values()):
            fh_out.write(line)
    os.rename(Functions_table_DOID_BTO_GOCC_temp, Functions_table_DOID_BTO_GOCC)'''

def Protein_2_Function_DOID_BTO_GOCC_UPS(GO_obo_Jensenlab, GO_obo, DOID_obo_current, BTO_obo_Jensenlab, Taxid_UniProtID_2_ENSPs_2_KEGGs,
        Protein_2_Function_and_Score_DOID_BTO_GOCC_STS,
        Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked,
        Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked_rescaled,
        Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized,
        Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked,
        Protein_2_Function_DOID_BTO_GOCC_UPS,
        DOID_BTO_GOCC_without_lineage,
        GO_CC_textmining_additional_etype=True,
        minimum_score = 1.5,
        alpha_22=0.5, beta_22=3, alpha_25=0.5, beta_25=3, alpha_26=0.5, beta_26=3):
    """
    discretize TextMining scores
    - reformat data --> DF
    - discretize scores
    - backtrack
    - translate ENSP to UniProtID (ignore things that can't be translated)
    ( - map Function to FuncEnum elsewhere )
    GO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "go_Jensenlab.obo")
    DOID_obo_current = os.path.join(DOWNLOADS_DIR, "DOID_obo_current.obo") # http://purl.obolibrary.org/obo/doid.obo
    BTO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "bto_Jensenlab.obo")  # static file
    Taxid_UniProtID_2_ENSPs_2_KEGGs = os.path.join(TABLES_DIR, "Taxid_UniProtID_2_ENSPs_2_KEGGs.txt")
    Protein_2_Function_and_Score_DOID_BTO_GOCC_STS = os.path.join(DOWNLOADS_DIR, "Protein_2_Function_and_Score_DOID_BTO_GOCC_STS.txt.gz")
    Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked = os.path.join(TABLES_DIR, "Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked.txt")
    Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized = os.path.join(TABLES_DIR, "Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized.txt")
    Protein_2_Function_DOID_BTO_GOCC_UPS = os.path.join(TABLES_DIR, "Protein_2_Function_DOID_BTO_GOCC_UPS.txt")
    alpha = 0.5
    max_score = 5
    """
    ### reformat data --> DF
    with open(Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked, "w") as fh_out:
        for line in tools.yield_line_uncompressed_or_gz_file(Protein_2_Function_and_Score_DOID_BTO_GOCC_STS):
            ENSP, funcName_2_score_arr_str, etype = line.split("\t")
            etype = etype.strip()
            taxid = ENSP.split(".")[0]
            funcName_2_score_list_temp = helper_convert_str_arr_2_nested_list(funcName_2_score_arr_str)
            for funcName, score in funcName_2_score_list_temp:
                fh_out.write("{}\t{}\t{}\t{}\t{}\n".format(taxid, etype, ENSP, funcName, score))
    df = pd.read_csv(Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked, sep='\t', names=["Taxid", "Etype", "ENSP", "funcName", "Score"])
    ### backtracking
    alternative_2_current_ID_dict = {}
    alternative_2_current_ID_dict.update(get_alternative_2_current_ID_dict(GO_obo_Jensenlab, upk=False))
    alternative_2_current_ID_dict.update(get_alternative_2_current_ID_dict(GO_obo, upk=False))
    # GOCC not needed yet, lineage_dict has GOCC terms but output file has normal GO terms, conversion happens at second backtracking step
    alternative_2_current_ID_dict.update(get_alternative_2_current_ID_dict(BTO_obo_Jensenlab, upk=True))
    alternative_2_current_ID_dict.update(get_alternative_2_current_ID_dict(DOID_obo_current, upk=True))
    # translate from alternative/alias to main name (synonym or obsolete funcName to current name)
    df["funcName"] = df["funcName"].apply(lambda x: alternative_2_current_ID_dict.get(x, x))
    # in case of redundant function 2 ENSP associations (with different scores) --> pick max score, drop rest
    df = df.loc[df.groupby(["Taxid", "Etype", "funcName", "ENSP"])["Score"].idxmax()]

    DAG = obo_parser.GODag(obo_file=GO_obo_Jensenlab, upk=False)
    DAG.load_obo_file(obo_file=DOID_obo_current, upk=True)
    DAG.load_obo_file(obo_file=BTO_obo_Jensenlab, upk=True)
    # GO_CC_textmining_additional_etype should always be False here --> replaces "GO" with "GOCC". Not necessary yet since, all terms still -22 not -20.
    lineage_dict_direct_parents = get_lineage_dict_for_DOID_BTO_GO(GO_obo_Jensenlab, DOID_obo_current, BTO_obo_Jensenlab, GO_CC_textmining_additional_etype=False, direct_parents_only=True)
    # backtracking with smart logic to propagate scores
    backtrack_TM_scores(df, lineage_dict_direct_parents, Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked)

    ### rescale Score per genome, per etype
    df = pd.read_csv(Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked, sep="\t")
    df_22 = df[df["Etype"] == -22] # Lars' etype is -22, David changes it to -20 (GOCC TextMining to distinguish it from GOCC)
    df_25 = df[df["Etype"] == -25]
    df_26 = df[df["Etype"] == -26]
    df_22 = rescale_scores(df_22, alpha=alpha_22)
    df_25 = rescale_scores(df_25, alpha=alpha_25)
    df_26 = rescale_scores(df_26, alpha=alpha_26)
    df = pd.concat([df_22, df_25, df_26])
    df.to_csv(Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked_rescaled, sep="\t", header=True, index=False)

    ### rescaled, backtracked, and filtered
    df = df[df["Score"] >= minimum_score]
    df_22 = df[df["Etype"] == -22]
    df_25 = df[df["Etype"] == -25]
    df_26 = df[df["Etype"] == -26]
    df_22 = df_22[df_22["Rescaled_score"] <= beta_22]
    df_25 = df_25[df_25["Rescaled_score"] <= beta_25]
    df_26 = df_26[df_26["Rescaled_score"] <= beta_26]
    df = pd.concat([df_22, df_25, df_26])
    df = df[["Taxid", "Etype", "ENSP", "funcName"]]
    df.to_csv(Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized, sep='\t', header=True, index=False)

    # backtrack a second time, simple backtracking this time, since already discretized
    # GOCC is etype -22, is changed to -20 at this point. GO_CC_textmining_additional_etype should be True (since GO is changed to GOCC before backtracking)
    lineage_dict_all_parents = get_lineage_dict_for_DOID_BTO_GO(GO_obo_Jensenlab, DOID_obo_current, BTO_obo_Jensenlab, GO_CC_textmining_additional_etype=True, direct_parents_only=False)
    DAG.load_obo_file(obo_file=GO_obo, upk=False)
    secondary_2_primaryTerm_dict, obsolete_terms_set = get_secondary_2_primaryTerm_dict_and_obsolete_terms_set(DAG)
    ENSP_2_UniProtID_dict = get_ENSP_2_UniProtID_dict(Taxid_UniProtID_2_ENSPs_2_KEGGs)
    backtrack_funcNames(df, lineage_dict_all_parents, secondary_2_primaryTerm_dict, obsolete_terms_set, ENSP_2_UniProtID_dict, Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked, Protein_2_Function_DOID_BTO_GOCC_UPS, DOID_BTO_GOCC_without_lineage, GO_CC_textmining_additional_etype=GO_CC_textmining_additional_etype)

def get_secondary_2_primaryTerm_dict_and_obsolete_terms_set(DAG):
    """
    secondary terms consist of obsolete and alternative terms
    primary terms are term.id and 'consider'
    DOWNLOADS_DIR = r"/scratch/dblyon/agotool/data/PostgreSQL/downloads"
    GO_basic_obo = os.path.join(DOWNLOADS_DIR, "go-basic.obo")
    UPK_obo = os.path.join(DOWNLOADS_DIR, "keywords-all.obo")
    GO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "go_Jensenlab.obo")
    DOID_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "doid_Jensenlab.obo")
    BTO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "bto_Jensenlab.obo") # static file
    DOID_obo_current = os.path.join(DOWNLOADS_DIR, "DOID_obo_current.obo")
    DAG = obo_parser.GODag(obo_file=GO_basic_obo, upk=False)
    DAG.load_obo_file(obo_file=UPK_obo, upk=True)
    DAG.load_obo_file(obo_file=DOID_obo_current, upk=True)
    DAG.load_obo_file(obo_file=BTO_obo_Jensenlab, upk=True)
    secondary_2_primaryTerm_dict, obsolete_terms_set = get_secondary_2_primaryTerm_dict_and_obsolete_terms_set(DAG)
    """
    secondary_2_primaryTerm_dict, obsolete_terms_set = {}, set()
    for term in DAG:
        if DAG[term].is_obsolete:
            obsolete_terms_set |= {term}
        term_id = DAG[term].id
        if term_id != term:
            secondary_2_primaryTerm_dict[term] = term_id
            term = term_id
        for alternative in DAG[term].alt_ids:
            if alternative not in secondary_2_primaryTerm_dict:
                secondary_2_primaryTerm_dict[alternative] = term
        consider_list = DAG[term].consider
        if len(consider_list) > 0:
            consider_ = consider_list[0]
            if consider_ not in secondary_2_primaryTerm_dict:
                secondary_2_primaryTerm_dict[term] = consider_
    return secondary_2_primaryTerm_dict, obsolete_terms_set


def backtrack_funcNames(df, lineage_dict_all_parents, secondary_2_primaryTerm_dict, obsolete_terms_set, ENSP_2_UniProtID_dict, Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked, Protein_2_Function_DOID_BTO_GOCC_UPS, DOID_BTO_GOCC_without_lineage, GO_CC_textmining_additional_etype=True):
    """
    df with ["Taxid", "Etype", "ENSP", "funcName"]
    """
    if GO_CC_textmining_additional_etype:
        df["Etype"] = df["Etype"].astype(int)
        cond_GOCC = df["Etype"] == -22
        df.loc[cond_GOCC, "Etype"] = -20
        df.loc[cond_GOCC, "funcName"] = df.loc[cond_GOCC, "funcName"].apply(lambda x: x.replace("GO:", "GOCC:"))

    terms_without_lineage = set()
    with open(Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked, "w") as fh_out_ENSP:
        with open(Protein_2_Function_DOID_BTO_GOCC_UPS, "w") as fh_out_UniProtID:
            fh_out_ENSP.write("Taxid\tEtype\tENSP\tfuncName\n")
            for taxid_etype_ENSP, group in df.groupby(["Taxid", "Etype", "ENSP"]):
                taxid, etype, ENSP = taxid_etype_ENSP
                UniProtID_list = ENSP_2_UniProtID_dict[ENSP]  # defaultdict
                funcName_list_backtracked = set(group.funcName.values)
                for funcName in group.funcName.values:
                    funcName, has_changed, is_obsolete = replace_obsolete_term_or_False(funcName, obsolete_terms_set, secondary_2_primaryTerm_dict)
                    if is_obsolete:
                        continue
                    try:
                        funcName_list_backtracked |= lineage_dict_all_parents[funcName]
                    except KeyError:
                        terms_without_lineage |= {funcName}
                for funcName in funcName_list_backtracked:
                    fh_out_ENSP.write("{}\t{}\t{}\t{}\n".format(taxid, etype, ENSP, funcName))

                #for UniProtID in UniProtID_list:
                fh_out_UniProtID.write("{}\t{}\t{}\n".format(ENSP, format_list_of_string_2_postgres_array(sorted(funcName_list_backtracked)), etype))
    with open(DOID_BTO_GOCC_without_lineage, "w") as fh_without_lineage:
        for term in sorted(terms_without_lineage):
            fh_without_lineage.write(term + "\n")

def get_ENSP_2_UniProtID_dict(Taxid_UniProtID_2_ENSPs_2_KEGGs):
    """
    :param Taxid_UniProtID_2_ENSPs_2_KEGGs: String (input file)
    :return: defaultdict (key: ENSP, val: list of UniProtIDs)
    """
    ENSP_2_UniProtID_dict = defaultdict(lambda: [])
    with open(Taxid_UniProtID_2_ENSPs_2_KEGGs, "r") as fh_in:
        for line in fh_in:
            taxid, UniProtID, ENSP, KEGG = line.split("\t")
            if len(ENSP) > 0:
                for ENSP in ENSP.split(";"):
                    ENSP_2_UniProtID_dict[ENSP].append(UniProtID)
    return ENSP_2_UniProtID_dict

def rescale_scores(df, alpha=0.5, max_score=5):
    """
    max_score: is not beta (cutoff), it's in case scores are transformed by e.g. 1e6 from float to int
    """
    # df = df.sort_values(["funcName", "Score"], ascending=[True, True])
    df = df.sort_values(["Taxid", "Etype", "funcName", "Score"], ascending=[True, True, True, True]) # discretize per genome, per etype
    df = df.reset_index(drop=True)
    df["Rescaled_score_orig"] = np.nan
    df["Rescaled_score"] = np.nan
    rescaled_score_orig_list, rescaled_score_equal_ranks_list = [], []
    # for DOID, group in df.groupby("funcName"):
    for taxid_etype_funcName, group in df.groupby(["Taxid", "Etype", "funcName"]):
        rescaled_score_group, rescaled_score_equal_ranks_group = [], []
        for score, gene_rank in zip(group.Score, list(range(1, group.shape[0] + 1))[::-1]):
            rescaled_score_group.append(math.pow(gene_rank, alpha) * math.pow((1 - score / max_score), (1 - alpha)))
        rescaled_score_orig_list += rescaled_score_group

        ### average rescaled_scores if original confidence_scores are equal
        sorted_Scores = group.Score.values
        vals, idx_start, count = np.unique(sorted_Scores, return_counts=True, return_index=True)
        start_stop_index_list = list(zip(idx_start, idx_start[1:])) + [(idx_start[-1], None)]
        for start_stop, num_genes in zip(start_stop_index_list, count):
            start, stop = start_stop
            if num_genes > 1:
                rescaled_score_equal_ranks_group += [np.median(rescaled_score_group[start:stop])] * num_genes
            else:
                rescaled_score_equal_ranks_group.append(rescaled_score_group[start])
        rescaled_score_equal_ranks_list += rescaled_score_equal_ranks_group

    df["Rescaled_score_orig"] = rescaled_score_orig_list
    df["Rescaled_score"] = rescaled_score_equal_ranks_list
    df = df.reset_index(drop=True)
    return df

def backtrack_TM_scores(df, lineage_dict_direct_parents_current, fn_out):
    """
    df with ENSP, DOID, and Score column
    """
    with open(fn_out, "w") as fh_out:
        fh_out.write("{}\t{}\t{}\t{}\t{}\n".format("Taxid", "Etype", "ENSP", "funcName", "Score"))
        for taxid_etype_ENSP, group in df.groupby(["Taxid", "Etype", "ENSP"]):
            funcName_2_score_list = list(zip(group.funcName, group.Score))
            funcName_2_score_list_backtracked_current, without_lineage_temp_current = helper_backtrack_funcName_2_score_list(funcName_2_score_list, lineage_dict_direct_parents_current, scale_by_1e6=False)
            taxid, etype, ENSP = taxid_etype_ENSP
            for funcName_score in funcName_2_score_list_backtracked_current:
                funcName, score = funcName_score
                fh_out.write("{}\t{}\t{}\t{}\t{}\n".format(taxid, etype, ENSP, funcName, score))

def helper_convert_str_arr_2_nested_list(funcName_2_score_arr_str):
    """
    funcName_2_score_arr_str = '{{"GO:0005777",0.535714},{"GO:0005783",0.214286},{"GO:0016021",3}}'
    --> [['GO:0005777', 0.535714], ['GO:0005783', 0.214286], ['GO:0016021', 3.0]]
    """
    funcName_2_score_list = []
    funcName_2_score_arr_str = [ele[1:] for ele in funcName_2_score_arr_str.replace('"', '').replace("'", "").split("},")]
    if len(funcName_2_score_arr_str) == 1:
        fs = funcName_2_score_arr_str[0][1:-2].split(",")
        funcName_2_score_list.append([fs[0], float(fs[1])])
    else:
        funcName_2_score_list_temp = [funcName_2_score_arr_str[0][1:].split(",")] + [ele.split(",") for ele in funcName_2_score_arr_str[1:-1]] + [funcName_2_score_arr_str[-1][:-2].split(",")]
        for sublist in funcName_2_score_list_temp:
            funcName_2_score_list.append([sublist[0], float(sublist[1])])
    return funcName_2_score_list

def get_alternative_2_current_ID_dict(fn_obo, upk=False):
    alternative_2_current_ID_dict = {}
    for rec in obo_parser.OBOReader(fn_obo, upk=upk):
        rec_id = rec.id
        for alternative in rec.alt_ids:
            alternative_2_current_ID_dict[alternative] = rec_id
    return alternative_2_current_ID_dict

def get_lineage_dict_for_DOID_BTO_GO(fn_go_basic_obo, fn_in_DOID_obo_Jensenlab, fn_in_BTO_obo_Jensenlab, GO_CC_textmining_additional_etype=False, direct_parents_only=False):
    lineage_dict = {}
    go_dag = obo_parser.GODag(obo_file=fn_go_basic_obo)
    ### key=GO-term, val=set of GO-terms (parents)
    for go_term_name in go_dag:
        GOTerm_instance = go_dag[go_term_name]
        if direct_parents_only:
            lineage_dict[go_term_name] = GOTerm_instance.get_direct_parents()
        else:
            lineage_dict[go_term_name] = GOTerm_instance.get_all_parents()
    if GO_CC_textmining_additional_etype:
        for go_term_name in go_dag:
            etype = str(get_entity_type_from_GO_term(go_term_name, go_dag))
            if etype == "-22": # GO-CC need be changed since unique names needed
                GOTerm_instance = go_dag[go_term_name]
                if direct_parents_only:
                    lineage_dict[go_term_name.replace("GO:", "GOCC:")] = {ele.replace("GO:", "GOCC:") for ele in GOTerm_instance.get_direct_parents()}
                else:
                    lineage_dict[go_term_name.replace("GO:", "GOCC:")] = {ele.replace("GO:", "GOCC:") for ele in GOTerm_instance.get_all_parents()}
    bto_dag = obo_parser.GODag(obo_file=fn_in_BTO_obo_Jensenlab)
    for term_name in bto_dag:
        Term_instance = bto_dag[term_name]
        if direct_parents_only:
            lineage_dict[term_name ] = Term_instance.get_direct_parents()
        else:
            lineage_dict[term_name ] = Term_instance.get_all_parents()
    doid_dag = obo_parser.GODag(obo_file=fn_in_DOID_obo_Jensenlab)
    for term_name in doid_dag:
        Term_instance = doid_dag[term_name]
        if direct_parents_only:
            lineage_dict[term_name ] = Term_instance.get_direct_parents()
        else:
            lineage_dict[term_name ] = Term_instance.get_all_parents()
    return lineage_dict

def helper_backtrack_funcName_2_score_list(funcName_2_score_list, lineage_dict_direct_parents, scale_by_1e6=True):
    """
    backtrack and propage text mining scores from Jensenlab without creating redundancy
    backtrack functions to root and propagate scores
        - only if there is no score for that term
        - if different scores exist for various children then
    convert scores from float to int (by scaling 1e6 and cutting)
    funcName_2_score_list = [['DOID:11613', 0.686827], ['DOID:1923', 0.817843], ['DOID:4', 1.982001], ['DOID:7', 1.815976]]
    lineage_dict["DOID:11613"] = {'DOID:11613', 'DOID:1923', 'DOID:2277', 'DOID:28', 'DOID:4', 'DOID:7'}
    funcName_2_score_list_backtracked = [['DOID:11613', 686827], ['DOID:1923', 817843], ['DOID:4', 1982001], ['DOID:7', 1815976], # previously set
    ['DOID:28', 686827], ['DOID:2277', 686827]} # backtracked new
    ['DOID:28', 817843], ['DOID:2277', 817843]} # backtracked new corrected
    set score directly that stem from textmining, propagate from child to parent term(s), if term has multiple children then the average of the scores is used
    visit all
    """
    funcName_2_score_dict_backtracked, without_lineage = {}, []
    # funcName_2_score_dict_backtracked: key=String, val=Float(if unique), List of Float(if averaged)
    # fill dict with all given values, these should be unique (funcName has only single value)
    for funcName_2_score in funcName_2_score_list:
        funcName, score = funcName_2_score
        if funcName not in funcName_2_score_dict_backtracked:
            funcName_2_score_dict_backtracked[funcName] = score
        else:
            print("helper_backtrack_funcName_2_score_list", funcName, funcName_2_score_dict_backtracked[funcName], score, " duplicates")

    # add all funcNames to iterable and extend with all parents
    visit_plan = deque()
    for child, score in funcName_2_score_list:
        visit_plan.append(child)

    while visit_plan:
        funcName = visit_plan.pop()
        try:
            direct_parents = lineage_dict_direct_parents[funcName]
        except KeyError:
            without_lineage.append(funcName)
            direct_parents = []
        score = funcName_2_score_dict_backtracked[funcName]
        for parent in direct_parents:
            if parent not in funcName_2_score_dict_backtracked: # propagate score, mark as such by using a list instead of float
                if isinstance(score, list):  # score is a list because it was propagated
                    funcName_2_score_dict_backtracked[parent] = score
                else:
                    funcName_2_score_dict_backtracked[parent] = [score]
                visit_plan.append(parent)
            else:
                if isinstance(funcName_2_score_dict_backtracked[parent], float):
                    continue  # don't change the value, since it is the original value
                elif isinstance(funcName_2_score_dict_backtracked[parent], list):  # add to it
                    if isinstance(score, list): # score is a list because it was propagated
                        funcName_2_score_dict_backtracked[parent] += score
                    else: # score is a float since original TM score
                        funcName_2_score_dict_backtracked[parent].append(score)
                else:
                    print("helper_backtrack_funcName_2_score_list", parent, funcName_2_score_dict_backtracked[parent], " type not known")
                    raise StopIteration

    # now calc median if multiple values exist --> deprecated --> use max
    funcName_2_score_list_backtracked = []
    if scale_by_1e6:
        for funcName in funcName_2_score_dict_backtracked:
            val = funcName_2_score_dict_backtracked[funcName]
            if isinstance(val, float):
                funcName_2_score_list_backtracked.append([funcName, int(val * 1e6)])
            else:
                # funcName_2_score_list_backtracked.append([funcName, int(median(val) * 1e6)])
                funcName_2_score_list_backtracked.append([funcName, int(max(val) * 1e6)])
    else:
        for funcName in funcName_2_score_dict_backtracked:
            val = funcName_2_score_dict_backtracked[funcName]
            if isinstance(val, float):
                funcName_2_score_list_backtracked.append([funcName, val])
            else:
                # funcName_2_score_list_backtracked.append([funcName, median(val)])
                funcName_2_score_list_backtracked.append([funcName, max(val)])

    return funcName_2_score_list_backtracked, set(without_lineage)

def replace_obsolete_term_or_False(term, obsolete_terms, secondary_2_primaryTerm_dict):
    try:
        term_new = secondary_2_primaryTerm_dict[term]
    except KeyError:
        term_new = term

    if term_new in obsolete_terms:
        is_obsolete = True
    else:
        is_obsolete = False

    if term_new == term:
        has_changed = False
    else:
        has_changed = True
    return term_new, has_changed, is_obsolete

##### RIP dead code
#def pickle_PMID_autoupdates(Lineage_table_STRING, Taxid_2_FunctionCountArray_table_STRING, output_list):
#     assert os.path.exists(Lineage_table_STRING)
#     assert os.path.exists(Taxid_2_FunctionCountArray_table_STRING)
#     taxid_2_proteome_count_dict, kegg_taxid_2_acronym_dict, year_arr, hierlevel_arr, entitytype_arr, functionalterm_arr, indices_arr, description_arr, category_arr, lineage_dict_enum, blacklisted_terms_bool_arr, ENSP_2_functionEnumArray_dict, taxid_2_tuple_funcEnum_index_2_associations_counts, etype_2_minmax_funcEnum, etype_cond_dict = output_list
#     pqo = query.PersistentQueryObject_STRING(low_memory=False, read_from_flat_files=True, from_pickle=False)
#     print("writing pickle dumps")
#     pickle.dump(pqo.taxid_2_proteome_count_dict, open(taxid_2_proteome_count_dict, "wb"))
#     pickle.dump(pqo.kegg_taxid_2_acronym_dict, open(kegg_taxid_2_acronym_dict, "wb"))
#     pickle.dump(pqo.year_arr, open(year_arr, "wb"))
#     pickle.dump(pqo.hierlevel_arr, open(hierlevel_arr, "wb"))
#     pickle.dump(pqo.entitytype_arr, open(entitytype_arr, "wb"))
#     pickle.dump(pqo.functionalterm_arr, open(functionalterm_arr, "wb"))
#     pickle.dump(pqo.indices_arr, open(indices_arr, "wb"))
#     pickle.dump(pqo.description_arr, open(description_arr, "wb"))
#     pickle.dump(pqo.category_arr, open(category_arr, "wb"))
#     pickle.dump(pqo.lineage_dict_enum, open(lineage_dict_enum, "wb"))
#     pickle.dump(pqo.blacklisted_terms_bool_arr, open(blacklisted_terms_bool_arr, "wb"))
#     pickle.dump(pqo.ENSP_2_functionEnumArray_dict, open(ENSP_2_functionEnumArray_dict, "wb"))
#     pickle.dump(pqo.taxid_2_tuple_funcEnum_index_2_associations_counts, open(taxid_2_tuple_funcEnum_index_2_associations_counts, "wb"))
#     pickle.dump(pqo.etype_2_minmax_funcEnum, open(etype_2_minmax_funcEnum, "wb"))
#     pickle.dump(pqo.etype_cond_dict, open(etype_cond_dict, "wb"))
#     print("done :)")

#def get_lineage_Reactome(fn_hierarchy): #, debug=False): # deprecated
#     lineage_dict = defaultdict(lambda: set())
#     child_2_parent_dict = get_child_2_direct_parent_dict_RCTM(fn_hierarchy)
#     # parent_2_children_dict = get_parent_2_child_dict_RCTM(fn_hierarchy)
#     # if not debug:
#     #     for parent, children in parent_2_children_dict.items(): #!!! why do I need this? lineage from children to parents is needed not from parents to all children
#     #         lineage_dict[parent] = children
#     for child in child_2_parent_dict:
#         parents = get_parents_iterative(child, child_2_parent_dict)
#         if child in lineage_dict:
#             lineage_dict[child].union(parents)
#         else:
#             lineage_dict[child] = parents
#    return lineage_dict


# def get_parent_2_child_dict_RCTM(fn_hierarchy): # deprecated
#     parent_2_children_dict = {}
#     with open(fn_hierarchy, "r") as fh_in:
#         for line in fh_in:
#             parent, child = line.split("\t")
#             child = child.strip()
#             if parent not in parent_2_children_dict:
#                 parent_2_children_dict[parent] = {child}
#             else:
#                 parent_2_children_dict[parent] |= {child}
#     return parent_2_children_dict


# def Protein_2_Function_table_PMID__and__reduce_Functions_table_PMID(fn_in_all_entities, fn_in_string_matches, fn_in_Taxid_2_Proteins_table_STRING, fn_in_Functions_table_PMID_temp, fn_out_Functions_table_PMID, fn_out_Protein_2_Function_table_PMID):
#     df_txtID = parse_textmining_entityID_2_proteinID(fn_in_all_entities)
#     df_stringmatches = parse_textmining_string_matches(fn_in_string_matches)
#     # sanity test that df_stringmatches.entity_id are all in df_txtID.textmining_id --> yes. textmining_id is a superset of entity_id --> after filtering df_txtID this is not true
#     entity_id = set(df_stringmatches["entity_id"].unique())
#     textmining_id = set(df_txtID.textmining_id.unique())
#     assert len(entity_id.intersection(textmining_id)) == len(entity_id)
#
#     # sanity check that there is a one to one mapping between textmining_id and ENSP --> no --> first remove all ENSPs that are not in DB
#     # --> simpler by filtering based on positive integers in species_id column ?
#     # get all ENSPs
#
#     ENSP_set = set()
#     with open(fn_in_Taxid_2_Proteins_table_STRING, "r") as fh:
#         for line in fh:
#             ENSP_set |= literal_eval(line.split("\t")[1])
#     # reduce DF to ENSPs in DB
#     cond = df_txtID["ENSP"].isin(ENSP_set)
#     print("reducing df_txtID from {} to {} rows".format(len(cond), sum(cond)))
#     df_txtID = df_txtID[cond]
#     # sanity check
#     assert len(df_txtID["textmining_id"].unique()) == len(df_txtID["ENSP"].unique())
#     # filter by ENSPs in DB --> TaxID_2_Protein_table_STRING.txt
#     # textminingID_2_ENSP_dict
#     entity_id_2_ENSP_dict = pd.Series(df_txtID["ENSP"].values, index=df_txtID["textmining_id"]).to_dict()
#
#     # reduce df_stringmatches to relevant entity_ids
#     cond = df_stringmatches["entity_id"].isin(df_txtID["textmining_id"].values)
#     print("reducing df_stringmatches from {} to {} rows".format(len(cond), sum(cond)))
#     df_stringmatches = df_stringmatches[cond]
#
#     # create an_2_function_set
#     # entity_id_2_PMID_dict
#     # map entity_id to ENSP
#     df_stringmatches_sub = df_stringmatches[["PMID", "entity_id"]]
#     entity_id_2_PMID_dict = df_stringmatches_sub.groupby("entity_id")["PMID"].apply(set).to_dict()
#
#     ENSP_2_PMID_dict = {}
#     entity_id_2_ENSP_no_mapping = []
#     multi_ENSP = []
#     for entity_id, PMID_set in entity_id_2_PMID_dict.items():
#         try:
#             ENSP = entity_id_2_ENSP_dict[entity_id]
#         except KeyError:
#             entity_id_2_ENSP_no_mapping.append(entity_id)
#             continue
#         if ENSP not in ENSP_2_PMID_dict:
#             ENSP_2_PMID_dict[ENSP] = PMID_set
#         else:
#             multi_ENSP.append([entity_id, ENSP])
#
#     assert len(entity_id_2_ENSP_no_mapping) == 0
#     assert len(multi_ENSP) == 0
#
#     # | etype | an | func_array |
#     etype = "-56"
#     with open(fn_out_Protein_2_Function_table_PMID, "w") as fh_out:
#         for ENSP, PMID_set in ENSP_2_PMID_dict.items():
#             PMID_with_prefix_list = ["PMID:" + str(PMID) for PMID in sorted(PMID_set)]
#             fh_out.write(ENSP + "\t" + "{" + str(PMID_with_prefix_list)[1:-1].replace(" ", "").replace("'", '"') + "}" + "\t" + etype + "\n")
#
#     # #!!! dependency on creating Functions_table_PMID.txt first
#     # reduce Functions_table_PMID.txt to PMIDs that are in Protein_2_Function_table_PMID.txt
#     PMID_set = set(df_stringmatches["PMID"].values)
#     # fn_temp = fn_out_Functions_table_PMID + "_temp"
#     # os.rename(fn_out_Functions_table_PMID, fn_temp)
#     PMID_not_relevant = []
#     with open(fn_in_Functions_table_PMID_temp, "r") as fh_in:
#         with open(fn_out_Functions_table_PMID, "w") as fh_out:
#             for line in fh_in:
#                 PMID_including_prefix = line.split("\t")[1]
#                 if int(PMID_including_prefix[5:]) in PMID_set:
#                     fh_out.write(line)
#                 else:
#                     PMID_not_relevant.append(PMID_including_prefix)

# def map_Name_2_AN(fn_in, fn_out, fn_dict, fn_no_mapping):
#     """
#     SMART and PFAM Protein_2_Function_table(s) contain names from parsing the
#     orig source, convert names to accessions
#     :param fn_in: String (Protein_2_Function_table_temp_SMART.txt)
#     :param fn_out: String (Protein_2_Function_table_SMART.txt)
#     :param fn_dict: String (Functions_table_SMART.txt
#     :param fn_no_mapping: String (missing mapping)
#     :return: NONE
#     """
#     print("map_Name_2_AN for {}".format(fn_in))
#     df = pd.read_csv(fn_dict, sep="\t", names=["name", "an"]) # names=["etype", "name", "an", "definition"])
#     name_2_an_dict = pd.Series(df["an"].values, index=df["name"]).to_dict()
#     df["name_v2"] = df["name"].apply(lambda x: x.replace("-", "_").lower())
#     name_2_an_dict_v2 = pd.Series(df["an"].values, index=df["name_v2"]).to_dict()
#     name_2_an_dict.update(name_2_an_dict_v2)
#     name_no_mapping_list = []
#     with open(fn_in, "r") as fh_in:
#         with open(fn_out, "w") as fh_out:
#             for line in fh_in:
#                 ENSP, name_array, etype_newline = line.split("\t")
#                 name_set = literal_eval(name_array)
#                 an_list = []
#                 for name in name_set:
#                     try:
#                         an_list.append(name_2_an_dict[name])
#                     except KeyError:
#                         # not in the lookup, therefore should be skipped since most likely obsolete in current version
#                         name_no_mapping_list.append(name)
#                 if an_list: # not empty
#                     fh_out.write(ENSP + "\t{" + str(sorted(an_list))[1:-1].replace(" ", "").replace("'", '"') + "}\t" + etype_newline)
#     with open(fn_no_mapping, "w") as fh_no_mapping:
#         fh_no_mapping.write("\n".join(sorted(set(name_no_mapping_list))))
