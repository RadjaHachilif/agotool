import os
# sys.path.insert(0, os.path.join(os.getcwd(), "python"))
# import variables_snakemake as variables
import variables
import create_SQL_tables_snakemake as cst
import download_resources_snakemake as drs
import tools
from importlib import reload
reload(cst)
reload(drs)
reload(tools)
import socket
hostname = socket.gethostname()
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


# RTCM
URL_RCTM_hierarchy = r"https://reactome.org/download/current/ReactomePathwaysRelation.txt"
RCTM_hierarchy = os.path.join(DOWNLOADS_DIR, "RCTM_hierarchy.tsv") 
URL_RCTM_descriptions = r"https://reactome.org/download/current/ReactomePathways.txt" 
RCTM_descriptions = os.path.join(DOWNLOADS_DIR, "RCTM_descriptions.tsv")
Protein_2_Function_table_RCTM = os.path.join(TABLES_DIR, "Protein_2_Function_table_RCTM.txt")
RCTM_associations = os.path.join(DOWNLOADS_DIR, "RCTM_associations.tsv") #/mnt/mnemo5/dblyon/agotool/data/PostgreSQL/downloads/RCTM_associations.tsv
Functions_table_RCTM = os.path.join(TABLES_DIR, "Functions_table_RCTM.txt")

# DOID
URL_DOID_obo_current = r"http://purl.obolibrary.org/obo/doid.obo"
DOID_obo_current = os.path.join(DOWNLOADS_DIR, "DOID_obo_current.obo")

# GO
URL_GO_obo = r"http://purl.obolibrary.org/obo/go/go-basic.obo"
GO_obo = os.path.join(DOWNLOADS_DIR, "go-basic.obo")
knowledge = os.path.join(DOWNLOADS_DIR, "knowledge.tsv") #/mnt/mnemo6/damian/STRING_derived_v11.5/go/knowledge.tsv
Protein_2_Function_table_GO = os.path.join(TABLES_DIR, "Protein_2_Function_table_GO.txt")

# UPK
URL_UPK_obo = r"http://www.uniprot.org/keywords/?query=&format=obo"
UPK_obo = os.path.join(DOWNLOADS_DIR, "keywords-all.obo")
Functions_table_UPK = os.path.join(TABLES_DIR, "Functions_table_UPK.txt")
Protein_2_Function_table_UPK = os.path.join(TABLES_DIR, "Protein_2_Function_table_UPK.txt")

# wget 'ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_*.dat.gz'
uniprot_SwissProt_dat = os.path.join(DOWNLOADS_DIR, "uniprot_sprot.dat.gz")
uniprot_TrEMBL_dat = os.path.join(DOWNLOADS_DIR, "uniprot_trembl.dat.gz")

uniprot_2_string = os.path.join(DOWNLOADS_DIR, "full_uniprot_2_string.jan_2018.clean.tsv")

# Interpro
URL_interpro_parent_2_child_tree = r"ftp://ftp.ebi.ac.uk/pub/databases/interpro/ParentChildTreeFile.txt"
interpro_parent_2_child_tree = os.path.join(DOWNLOADS_DIR, "interpro_parent_2_child_tree.txt")
URL_interpro_AN_2_name = r"ftp://ftp.ebi.ac.uk/pub/databases/interpro/entry.list"
interpro_AN_2_name = os.path.join(DOWNLOADS_DIR, "interpro_AN_2_name.txt") # InterPro_name_2_AN
Functions_table_InterPro = os.path.join(TABLES_DIR, "Functions_table_InterPro.txt")
Protein_2_Function_table_InterPro = os.path.join(TABLES_DIR, "Protein_2_Function_table_InterPro.txt")

uniprot_2_string = "/mnt/mnemo6/damian/STRING_derived_v11.5/uniprot_2020/full_uniprot_2_string.tsv"
string_2_interpro = os.path.join(DOWNLOADS_DIR, "string_2_interpro.dat.gz") 
URL_uniprot_2_interpro = r"https://ftp.ebi.ac.uk/pub/databases/interpro/uniparc_match.tar.gz"
uniprot_2_interpro = os.path.join(DOWNLOADS_DIR, "uniparc_match.tar.gz") 

# DOID_BTO_GOCC
URL_integrated_function_2_description_Jensenlab = r"http://download.jensenlab.org/aGOtool/integrated_function2description.tsv.gz"
Function_2_Description_DOID_BTO_GO_down = os.path.join(DOWNLOADS_DIR, "Function_2_Description_DOID_BTO_GO.txt.gz")
Functions_table_DOID_BTO_GOCC = os.path.join(TABLES_DIR, "Functions_table_DOID_BTO_GOCC.txt")
Protein_2_Function_DOID_BTO_GOCC_UPS = os.path.join(TABLES_DIR, "Protein_2_Function_DOID_BTO_GOCC_UPS.txt")
Protein_2_Function_and_Score_DOID_BTO_GOCC_STS = os.path.join(DOWNLOADS_DIR, "Protein_2_Function_and_Score_DOID_BTO_GOCC_STS.txt.gz")
Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked = os.path.join(TABLES_DIR, "Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked.txt")
Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked_rescaled = os.path.join(TABLES_DIR, "Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked_rescaled.txt")
Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized = os.path.join(TABLES_DIR, "Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized.txt")
Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked = os.path.join(TABLES_DIR, "Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked.txt")
DOID_BTO_GOCC_without_lineage = os.path.join(TABLES_DIR, "DOID_BTO_GOCC_without_lineage.txt")
BTO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "bto_Jensenlab.obo") # static file

#Blacklist_Jensenlab
URL_blacklisted_terms_Jensenlab = r"http://download.jensenlab.org/aGOtool/all_hidden.tsv"
Blacklisted_terms_Jensenlab = os.path.join(DOWNLOADS_DIR, "blacklisted_terms_Jensenlab.txt")

# DOID
URL_doid_obo = r"http://download.jensenlab.org/aGOtool/doid.obo"
DOID_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "doid_Jensenlab.obo")

# GO
URL_go_obo_Jensenlab = r"http://download.jensenlab.org/aGOtool/go.obo"
GO_obo_Jensenlab = os.path.join(DOWNLOADS_DIR, "go_Jensenlab.obo")
Functions_table_GO_Jensenlab = os.path.join(TABLES_DIR, "Functions_table_GO_Jensenlab.txt")
Functions_table_GO = os.path.join(TABLES_DIR, "Functions_table_GO.txt")

# WikiPathways
URL_WikiPathways_GMT = r"http://data.wikipathways.org/current/gmt"
Human_WikiPathways_gmt = os.path.join(DOWNLOADS_DIR, "wikipathways-Homo_sapiens.gmt")
WikiPathways_organisms_metadata = os.path.join(DOWNLOADS_DIR, "WikiPathways_organisms_metadata.tsv") # static
STRING_EntrezGeneID_2_STRING = os.path.join(DOWNLOADS_DIR, "STRING_v11_all_organisms_entrez_2_string_2018.tsv")

Functions_table_WikiPathways = os.path.join(TABLES_DIR, "Functions_table_WikiPathways.txt")
Protein_2_Function_table_WikiPathways = os.path.join(TABLES_DIR, "Protein_2_Function_table_WikiPathways_STS.txt")

# KEGG
KEGG_dir = DOWNLOADS_DIR # fake mock
KEGG_pathway = os.path.join(KEGG_dir, "pathway.list") #https://www.genome.jp/kegg/pathway.html#metabolism
Functions_table_KEGG = os.path.join(TABLES_DIR, "Functions_table_KEGG.txt")
#KEGG_organisms_dir = os.path.join(KEGG_dir, r"pathway/organisms")
Taxid_UniProtID_2_ENSPs_2_KEGGs = os.path.join(TABLES_DIR, "Taxid_UniProtID_2_ENSPs_2_KEGGs.txt")
Protein_2_Function_table_KEGG_UPS = os.path.join(TABLES_DIR, "Protein_2_Function_table_KEGG_UPS.txt")
Protein_2_Function_table_KEGG_UPS_ENSP_benchmark = os.path.join(TABLES_DIR, "Protein_2_Function_table_KEGG_UPS_ENSP_benchmark.txt")
KEGG_entry_no_pathway_annotation = os.path.join(TABLES_DIR, "KEGG_entry_no_pathway_annotation.txt")
Protein_2_Function_table_KEGG = os.path.join(TABLES_DIR, "Protein_2_Function_table_KEGG.txt")
KEGG_TaxID_2_acronym_table = os.path.join(TABLES_DIR, "KEGG_Taxid_2_acronym_table_STS_FIN.txt")
kegg_benchmarking = os.path.join(KEGG_dir, "kegg_benchmarking.CONN_maps_in.v11.nothing_blacklisted.tsv") #on Damian

# STRING
Functions_table_STRING_all_but_PMID = os.path.join(TABLES_DIR, "Functions_table_STRING_all_but_PMID.txt")
Protein_2_Function_table_STRING_all_but_PMID = os.path.join(TABLES_DIR, "Protein_2_Function_table_STRING_all_but_PMID.txt")


# PFAM
Functions_table_PFAM = os.path.join(TABLES_DIR, "Functions_table_PFAM.txt")
#Functions_table_PFAM_no_mapping = os.path.join(TABLES_DIR, "Functions_table_PFAM_no_mapping.txt")       
Protein_2_Function_table_PFAM = "/mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/Protein_2_Function_table_PFAM.txt"  #os.path.join(TABLES_DIR, "Protein_2_Function_table_PFAM.txt")
PFAM_clans = os.path.join(DOWNLOADS_DIR, "Pfam-A.clans.tsv") 
map_name_2_an_PFAM = os.path.join(TABLES_DIR, "map_name_2_an_PFAM.txt")
URL_PFAM_clans = "ftp://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.clans.tsv.gz"

# SMART 
Functions_table_SMART = os.path.join(TABLES_DIR, "Functions_table_SMART.txt")
Protein_2_Function_table_SMART ="/mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/Protein_2_Function_table_SMART.txt" # os.path.join(TABLES_DIR, "Protein_2_Function_table_SMART.txt")
URL_descriptions = "http://smart.embl-heidelberg.de/smart/descriptions.pl"
descriptions = os.path.join(DOWNLOADS_DIR, "descriptions.pl") 
dom_prot_full = os.path.join(DOWNLOADS_DIR, "string11_dom_prot_full.sql")
map_name_2_an_SMART = os.path.join(TABLES_DIR, "map_name_2_an_SMART.txt")

# STRING clusters
Functions_table_STRING_clusters = os.path.join(TABLES_DIR, "Functions_table_STRING_clusters.txt")
Protein_2_Function_table_STRING_clusters = os.path.join(TABLES_DIR, "Protein_2_Function_table_STRING_clusters.txt")
Taxid_2_Proteins_table_STRING = os.path.join(TABLES_DIR, "Taxid_2_Proteins_table_STRING.txt") #static

URL_integrated_protein_2_function_Jensenlab = r"http://download.jensenlab.org/aGOtool/integrated_protein2function.tsv.gz"

Lineage_table_UPS_FIN = os.path.join(TABLES_DIR, "Lineage_table_STS_FIN.txt")
Lineage_table_UPS_no_translation = os.path.join(TABLES_DIR, "Lineage_table_UPS_no_translation.txt")
Lineage_table_UPS_hr = os.path.join(TABLES_DIR, "Lineage_table_UPS_hr.txt") # Human Readable


###################################################################################################
##################################   download resources  ##########################################
# download_SMART_descriptions
drs.download_requests(URL_descriptions, descriptions)

# download_RCTM_hierarchy
drs.download_requests(URL_RCTM_hierarchy, RCTM_hierarchy)

# download_DOID_obo_current
drs.download_requests(URL_DOID_obo_current, DOID_obo_current, verbose)

# download_GO_obo
drs.download_requests(URL_GO_obo, GO_obo, verbose)

# download_UPK_obo
drs.download_requests(URL_UPK_obo, UPK_obo, verbose)

# download_ontology_Interpro
drs.download_gzip_file(URL_interpro_parent_2_child_tree, interpro_parent_2_child_tree, verbose)

# download_Protein_2_Function_and_Score_DOID_BTO_GOCC_STS
drs.download_requests(URL_integrated_protein_2_function_Jensenlab, Protein_2_Function_and_Score_DOID_BTO_GOCC_STS, verbose)

# download_descriptions_DOID_BTO_GO
drs.download_requests(URL_integrated_function_2_description_Jensenlab, Function_2_Description_DOID_BTO_GO_down, verbose)

# download_Blacklist_Jensenlab
drs.download_requests(URL_blacklisted_terms_Jensenlab, Blacklisted_terms_Jensenlab, verbose)

# download_DOID_obo_Jensenlab
drs.download_requests(URL_doid_obo, DOID_obo_Jensenlab, verbose)

# download_GO_obo_Jensenlab
drs.download_requests(URL_go_obo_Jensenlab, GO_obo_Jensenlab, verbose)

# download_WikiPathways
drs.download_WikiPathways(URL_WikiPathways_GMT, DOWNLOADS_DIR, Human_WikiPathways_gmt)

# download_descriptions_Interpro
drs.download_gzip_file(URL_interpro_AN_2_name, interpro_AN_2_name, verbose)

## download_uniprot_2_interpro
#drs.download_gzip_file(URL_uniprot_2_interpro, uniprot_2_interpro, verbose)

# download_descriptions_RCTM
drs.download_requests(URL_RCTM_descriptions, RCTM_descriptions, verbose)

# download_PFAM
drs.download_requests(URL_PFAM_clans, PFAM_clans)

###################################################################################################
#############################   create functions tables  ##########################################

# Functions_table_GO_Jensenlab
is_upk = False
cst.Functions_table_GO_or_UPK(GO_obo_Jensenlab, Functions_table_GO_Jensenlab, is_upk)

# Functions_table_GO
is_upk = False
cst.Functions_table_GO_or_UPK(GO_obo, Functions_table_GO, is_upk)

# Functions_table_UPK
is_upk = True
cst.Functions_table_GO_or_UPK(UPK_obo, Functions_table_UPK, is_upk)

# Functions_table_InterPro
cst.Functions_table_InterPro(interpro_AN_2_name, interpro_parent_2_child_tree, Functions_table_InterPro)

# Functions_table_KEGG
cst.Functions_table_KEGG(KEGG_pathway, Functions_table_KEGG, verbose)

# Functions_table_DOID_BTO_GOCC # these are not being filtered to relevant ones, but since number is small (~20k), the impact should be negligible
GO_CC_textmining_additional_etype = True

cst.Functions_table_DOID_BTO_GOCC(Function_2_Description_DOID_BTO_GO_down, BTO_obo_Jensenlab, DOID_obo_Jensenlab, GO_obo_Jensenlab, Blacklisted_terms_Jensenlab, Functions_table_DOID_BTO_GOCC, GO_CC_textmining_additional_etype, NUMBER_OF_PROCESSES_sorting, verbose)

# Protein_2_Function__and__Functions_table_WikiPathways_STS
cst.Protein_2_Function__and__Functions_table_WikiPathways_STS(WikiPathways_organisms_metadata, STRING_EntrezGeneID_2_STRING, Human_WikiPathways_gmt, Functions_table_WikiPathways, Protein_2_Function_table_WikiPathways, verbose=True)
 
# Functions_table_PFAM
cst.Functions_table_PFAM(PFAM_clans, Functions_table_PFAM, map_name_2_an_PFAM)

# Protein_2_Function_table_RCTM__and__Function_table_RCTM
cst.Protein_2_Function_table_RCTM__and__Function_table_RCTM(RCTM_associations, RCTM_descriptions, RCTM_hierarchy, Protein_2_Function_table_RCTM, Functions_table_RCTM, NUMBER_OF_PROCESSES_sorting)

# Functions_table_RCTM
cst.Functions_table_RCTM(RCTM_descriptions, RCTM_hierarchy, Functions_table_RCTM)

# Functions_table_SMART
### Parameters
max_len_description = 250
cst.Functions_table_SMART(descriptions, Functions_table_SMART, max_len_description, map_name_2_an_SMART)

# Functions_table_STRING_all_but_PMID
fn_list_str = [Functions_table_InterPro,
               Functions_table_KEGG,
               Functions_table_PFAM,
               Functions_table_GO,
               Functions_table_UPK,
               Functions_table_RCTM,
               Functions_table_SMART, # does not change
               Functions_table_DOID_BTO_GOCC,
               Functions_table_STRING_clusters,
               Functions_table_WikiPathways]

cst.concatenate_Functions_tables_no_enum(fn_list_str, Functions_table_STRING_all_but_PMID, NUMBER_OF_PROCESSES_sorting)

###################################################################################################
########################   create protein to  functions tables  ###################################

# Protein_2_Function_table_InterPro
cst.string_2_interpro(uniprot_2_string, uniprot_2_interpro, string_2_interpro)
cst.Protein_2_Function_table_InterPro(string_2_interpro, Functions_table_InterPro, interpro_parent_2_child_tree, Protein_2_Function_table_InterPro, NUMBER_OF_PROCESSES_sorting, verbose=True)

# Protein_2_Function_table_KEGG
cst.Protein_2_Function_table_KEGG(kegg_benchmarking, Protein_2_Function_table_KEGG, KEGG_TaxID_2_acronym_table, NUMBER_OF_PROCESSES_sorting)

# Protein_2_Function_table_SMART_and_PFAM_temp
cst.Protein_2_Function_table_SMART_and_PFAM_temp(dom_prot_full, map_name_2_an_SMART, map_name_2_an_PFAM, Protein_2_Function_table_SMART, Protein_2_Function_table_PFAM, NUMBER_OF_PROCESSES_sorting, verbose=True)

# Protein_2_Function_table_GO
cst.Protein_2_Function_table_GO(GO_obo, knowledge, Protein_2_Function_table_GO, NUMBER_OF_PROCESSES_sorting, verbose=True)

# Protein_2_Function_table_UniProtKeyword
cst.Protein_2_Function_table_UniProtKeyword(Functions_table_UPK, GO_obo, uniprot_SwissProt_dat, uniprot_TrEMBL_dat, uniprot_2_string, Protein_2_Function_table_UPK, NUMBER_OF_PROCESSES_sorting,  verbose=True)

# Protein_2_Function_DOID_BTO_GOCC_UPS
minimum_score = 1.5
alpha_22 = 0.2
beta_22 = 0.7
alpha_25 = 0.2
beta_25 = 0.7
alpha_26 = 0.2
beta_26 = 0.7
GO_CC_textmining_additional_etype = True
 
cst.Protein_2_Function_DOID_BTO_GOCC_UPS(GO_obo_Jensenlab, GO_obo, DOID_obo_current, BTO_obo_Jensenlab, Taxid_UniProtID_2_ENSPs_2_KEGGs, Protein_2_Function_and_Score_DOID_BTO_GOCC_STS, Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked, Protein_2_Function_and_Score_DOID_BTO_GOCC_STS_backtracked_rescaled, Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized, Protein_2_Function_DOID_BTO_GOCC_STS_backtracked_discretized_backtracked, Protein_2_Function_DOID_BTO_GOCC_UPS, DOID_BTO_GOCC_without_lineage, GO_CC_textmining_additional_etype=GO_CC_textmining_additional_etype, minimum_score=minimum_score, alpha_22=alpha_22, beta_22=beta_22, alpha_25=alpha_25, beta_25=beta_25, alpha_26=alpha_26, beta_26=beta_26)

# updating Taxid_2_Proteins_table_STRING
fn_in_protein_shorthands = os.path.join(DOWNLOADS_DIR, "protein.shorthands.v11.txt")
cst.Taxid_2_Proteins_table(fn_in_protein_shorthands, Taxid_2_Proteins_table_STRING, NUMBER_OF_PROCESSES_sorting, verbose=True)

# Protein_2_Function_table_STRING
fn_list_str = [Protein_2_Function_DOID_BTO_GOCC_UPS,
               Protein_2_Function_table_InterPro,
               Protein_2_Function_table_KEGG,
               Protein_2_Function_table_SMART,
               Protein_2_Function_table_PFAM,
               Protein_2_Function_table_GO,
               Protein_2_Function_table_UPK,
               Protein_2_Function_table_RCTM,
               Protein_2_Function_table_STRING_clusters,
               Protein_2_Function_table_WikiPathways
               ]
cst.Protein_2_Function_table_STRING(fn_list_str, Taxid_2_Proteins_table_STRING, Protein_2_Function_table_STRING_all_but_PMID, NUMBER_OF_PROCESSES_sorting)



















