import os, sys
from collections import defaultdict
import psycopg2, math
import pytest # should this be disabled for performance later?

# import user modules
sys.path.insert(0, os.path.abspath(os.path.realpath(__file__)))
import variables, obo_parser


UNSIGNED_2_SIGNED_CONSTANT = int(math.pow(2, 63))
FN_KEYWORDS = variables.FN_KEYWORDS
FN_GO_SLIM = variables.FN_GO_SLIM
FN_GO_BASIC = variables.FN_GO_BASIC
VERSION_ = variables.VERSION_

upkTerm_2_functionAN_dict = {u'Biological process': u'UPK:9999',
                             u'Cellular component': u'UPK:9998',
                             u'Coding sequence diversity': u'UPK:9997',
                             u'Developmental stage': u'UPK:9996',
                             u'Disease': u'UPK:9995',
                             u'Domain': u'UPK:9994',
                             u'Ligand': u'UPK:9993',
                             u'Molecular function': u'UPK:9992',
                             u'Post-translational modification': u'UPK:9991',
                             u'PTM': u'UPK:9991',
                             u'Technical term': u'UPK:9990'}

humanName_2_functionAN_dict = {u"BP": u"GO:0008150",
                               u"CP": u"GO:0005575",
                               u"MF": u"GO:0003674",
                               u"Biological Process": u"GO:0008150",
                               u"Cellular Component": u"GO:0005575",
                               u"Molecular Function": u"GO:0003674"}

functionType_term_2_an_dict = {"UPK": upkTerm_2_functionAN_dict,
                               "GO": humanName_2_functionAN_dict}

id_2_entityTypeNumber_dict = {'GO:0003674': "-23",  # 'Molecular Function',
                              'GO:0005575': "-22",  # 'Cellular Component',
                              'GO:0008150': "-21",  # 'Biological Process',
                              'UPK:9990': "-51",  # 'Technical term',
                              'UPK:9991': "-51",  # 'PTM',
                              'UPK:9992': "-51",  # 'Molecular function',
                              'UPK:9993': "-51",  # 'Ligand',
                              'UPK:9994': "-51",  # 'Domain',
                              'UPK:9995': "-51",  # 'Disease',
                              'UPK:9996': "-51",  # 'Developmental stage',
                              'UPK:9997': "-51",  # 'Coding sequence diversity',
                              'UPK:9998': "-51",  # 'Cellular component',
                              'UPK:9999': "-51",  # 'Biological process'
                              'KEGG': "-52"}


def get_cursor():
    platform_ = sys.platform
    if platform_ == "linux":
        try:
            USER = os.environ['POSTGRES_USER']
            PWD = os.environ['POSTGRES_PASSWORD']
            DBNAME = os.environ['POSTGRES_DB']
            HOST = 'db'
            PORT = '5432'
        except KeyError:
            print("query.py sais there is something wrong with the Postgres config")
            raise StopIteration
        return get_cursor_docker(host=HOST, dbname=DBNAME, user=USER, password=PWD, port=PORT)
    elif platform_ == "darwin":
        if not variables.DB_DOCKER: # use local Postgres
            return get_cursor_ody()
        else: # connect to docker Postgres container
            # USER = "postgres"
            # PWD = "USE_YOUR_PASSWORD"
            # DBNAME = "agotool"
            HOST = 'localhost'
            PORT = '5432'
            # fn = os.path.join(os.path.dirname(os.path.abspath(os.path.realpath(__file__))), "env_file")
            # print(fn)
            # param_2_val_dict = parse_env_file(fn)
            param_2_val_dict = variables.param_2_val_dict
            # return get_cursor_ody_connect_2_docker(host=HOST, dbname=DBNAME, user=USER, password=PWD, port=PORT)
            return get_cursor_ody_connect_2_docker(host=HOST, dbname=param_2_val_dict["POSTGRES_DB"], user=param_2_val_dict["POSTGRES_USER"], password=param_2_val_dict["POSTGRES_PASSWORD"], port=PORT)
    else:
        print("query.get_cursor() doesn't know how to connect to Postgres")
        raise StopIteration

def get_cursor_docker(host, dbname, user, password, port):
    """
    e.g.
    import os
    user = os.environ['POSTGRES_USER']
    pwd = os.environ['POSTGRES_PASSWORD']
    db = os.environ['POSTGRES_DB']
    host = 'db'
    port = '5432'
    cursor = get_cursor_docker(user=user, password=pwd, host=host, port=port, dbname=db)
    # Sqlalchemy version: engine = create_engine('postgres://%s:%s@%s:%s/%s' % (user, pwd, host, port, db))
    """
    # Define our connection string
    # conn_string = "host='{}' dbname='{}' user='{}' password='{}'".format(host, dbname, user, password)

    # engine = create_engine('postgres://%s:%s@%s:%s/%s' % (user, pwd, host, port, db))
    conn_string = "host='{}' dbname='{}' user='{}' password='{}' port='{}'".format(host, dbname, user, password, port)
    # get a connection, if a connect cannot be made an exception will be raised here
    conn = psycopg2.connect(conn_string)

    # conn.cursor will return a cursor object, you can use this cursor to perform queries
    cursor = conn.cursor()
    return cursor

def get_cursor_ody(dbname='agotool'):
    """
    :param dbname:
    :return: DB Cursor instance object
    """
    # Define our connection string
    conn_string = "dbname='{}'".format(dbname)

    # get a connection, if a connect cannot be made an exception will be raised here
    conn = psycopg2.connect(conn_string)

    # conn.cursor will return a cursor object, you can use this cursor to perform queries
    cursor = conn.cursor()
    return cursor

def get_cursor_ody_connect_2_docker(host, dbname, user, password, port):
    conn_string = "host='{}' dbname='{}' user='{}' password='{}' port='{}'".format(host, dbname, user, password, port)
    # get a connection, if a connect cannot be made an exception will be raised here
    conn = psycopg2.connect(conn_string)

    # conn.cursor will return a cursor object, you can use this cursor to perform queries
    cursor = conn.cursor()
    return cursor

def query_example():
    cursor = get_cursor()
    cursor.execute("SELECT * FROM functions LIMIT 5")
    records = cursor.fetchall()
    cursor.close()
    print(records)

def get_function_type_id_2_name_dict(function_type):
    cursor = get_cursor()
    sql_statement = "SELECT functions.an, functions.name FROM functions WHERE functions.type='{}'".format(function_type)
    cursor.execute(sql_statement)
    result = cursor.fetchall()
    id_2_name_dict = {}
    for res in result:
        id_ = res[0]
        name = res[1]
        id_2_name_dict[id_] = name
    cursor.close()
    return id_2_name_dict

def map_secondary_2_primary_ANs(ans_list):
    """
    map secondary UniProt ANs to primary ANs,
    AN only in dict if mapping exists
    :param ans_list: ListOfString
    :return: Dict (key: String(Secondary AN), val: String(Primary AN))
    """
    cursor = get_cursor()
    ans_list = str(ans_list)[1:-1]
    sql_statement = "SELECT protein_secondary_2_primary_an.sec, protein_secondary_2_primary_an.pri FROM protein_secondary_2_primary_an WHERE protein_secondary_2_primary_an.sec IN({})".format(ans_list)
    cursor.execute(sql_statement)
    result = cursor.fetchall()
    secondary_2_primary_dict = {}
    for res in result:
        secondary = res[0]
        primary = res[1]
        secondary_2_primary_dict[secondary] = primary
    cursor.close()
    return secondary_2_primary_dict


class PersistentQueryObject:
    """
    aGOtool version
    used to query protein 2 functional associations
    only protein_2_function is queried in Postgres,
    everything else is in memory but still deposited in the DB any way
    """
    def __init__(self):
        # self.version_ = VERSION_
        # if self.version_ == "aGOtool":
        self.secondary_2_primary_an_dict = self.get_secondary_2_primary_an_dict()
        # else:
        #     self.secondary_2_primary_an_dict = None
        self.type_2_association_dict = self.get_type_2_association_dict()
        self.go_slim_set = self.get_go_slim_terms()
        self.KEGG_functions_set = self.get_functions_set_from_functions(function_type="KEGG")
        self.DOM_functions_set = self.get_functions_set_from_functions(function_type="DOM")
        # precompute set of functions to restrict funtional associations to
        #  might need speed overhaul #!!!
        self.UPK_functions_set = self.get_ontology_set_of_type("UPK", "")
        self.BP_basic_functions_set = self.get_ontology_set_of_type("BP", "basic")
        self.MF_basic_functions_set = self.get_ontology_set_of_type("MF", "basic")
        self.CP_basic_functions_set = self.get_ontology_set_of_type("CP", "basic")

        ##### pre-load go_dag and goslim_dag (obo files) for speed, also filter objects
        upk_dag = obo_parser.GODag(obo_file=FN_KEYWORDS, upk=True)
        self.upk_dag = upk_dag

        goslim_dag = obo_parser.GODag(obo_file=FN_GO_SLIM)
        self.goslim_dag = goslim_dag

        # go_dag.update_association() #???
        go_dag = obo_parser.GODag(obo_file=FN_GO_BASIC)
        for go_term in go_dag.keys():
            _ = go_dag[go_term].get_all_parents()
        self.go_dag = go_dag

        # for backtracking
        self.child_2_parent_dict = self.get_child_2_parent_dict()

        KEGG_pseudo_dag = obo_parser.KEGG_pseudo_dag()
        self.KEGG_pseudo_dag = KEGG_pseudo_dag

        DOM_pseudo_dag = obo_parser.DOM_pseudo_dag()
        self.DOM_pseudo_dag = DOM_pseudo_dag

    @staticmethod
    def get_secondary_2_primary_an_dict():
        secondary_2_primary_dict = {}
        cursor = get_cursor()
        sql_statement = "SELECT protein_secondary_2_primary_an.sec, protein_secondary_2_primary_an.pri FROM protein_secondary_2_primary_an;"
        cursor.execute(sql_statement)
        result = cursor.fetchall()
        for res in result:
            secondary = res[0]
            primary = res[1]
            secondary_2_primary_dict[secondary] = primary
        cursor.close()
        return secondary_2_primary_dict

    @staticmethod
    def get_type_2_association_dict():
        cursor = get_cursor()
        sql_statement = "SELECT ontologies.child, ontologies.parent, ontologies.type FROM ontologies;"
        cursor.execute(sql_statement)
        result = cursor.fetchall()
        type_2_association_dict = {}
        for res in result:
            child = res[0]
            parent = res[1]
            type_ = res[2]
            if type_ in type_2_association_dict:
                type_2_association_dict[type_].update([child, parent])
            else:
                type_2_association_dict[type_] = {child, parent}
        cursor.close()
        return type_2_association_dict

    @staticmethod
    def get_go_slim_terms():
        cursor = get_cursor()
        sql_statement = "SELECT go_2_slim.an FROM go_2_slim;"
        cursor.execute(sql_statement)
        result = cursor.fetchall()
        go_slim_set = set()
        for res in result:
            go_slim_set.update([res[0]])
        cursor.close()
        return go_slim_set

    @staticmethod
    def get_functions_set_from_functions(function_type):
        cursor = get_cursor()
        cursor.execute("SELECT functions.an FROM functions WHERE functions.type='{}'".format(function_type))
        result = cursor.fetchall()
        functions_set = set()
        for res in result:
            functions_set.update([res[0]])
        cursor.close()
        return functions_set

    def map_secondary_2_primary_ANs(self, ans_list):
        """
        def map_secondary_2_primary_ANs_v1_slow(self, ans_list):
            secondary_ans_2_replace = set(self.secondary_2_primary_an_dict.keys()).intersection(set(ans_list))
            return dict((secondary_an, self.secondary_2_primary_an_dict[secondary_an]) for secondary_an in secondary_ans_2_replace)

        :param ans_list: List of String
        :return: secondary_2_primary_dict (key: String(Secondary AN), val: String(Primary AN))
        """
        secondary_2_primary_dict_temp = {}
        for secondary in ans_list:
            try:
                secondary_2_primary_dict_temp[secondary] = self.secondary_2_primary_an_dict[secondary]
            except KeyError:
                continue
        return secondary_2_primary_dict_temp

    def get_ontology_set_of_type(self, function_type, go_slim_or_basic):
        """
        select all parents and children of given type_
        "UPK": -51
        "BP": -21
        "MF": -22
        "CP": -23
        "all_GO": [-21, -22, -23]

        # choices = (("all_GO", "all GO categories"), ("BP", "GO Biological Process"),
        ("CP", "GO Celluar Compartment"), ("MF", "GO Molecular Function"),
        ("UPK", "UniProt keywords"))

        'GO:0003674': "-23",  # 'Molecular Function',
        'GO:0005575': "-22",  # 'Cellular Component',
        'GO:0008150': "-21",  # 'Biological Process',
        'UPK:9990': "-51",  # 'Technical term',

        :param function_type: String (one of "all_GO", "UPK", "BP", "MF", "CP")
        :param go_slim_or_basic: String ("slim" or "basic")
        :return: Set of String
        """
        #!!! potential speed up with "|=" instead of ".union()"
        if function_type == "all_GO":
            if go_slim_or_basic == "basic":
                return self.type_2_association_dict[-21].union(self.type_2_association_dict[-22]).union(self.type_2_association_dict[-23])
            else: # slim
                return self.go_slim_set

        elif function_type == "UPK":
            return self.type_2_association_dict[-51]

        elif function_type == "BP":
            if go_slim_or_basic == "basic":
                return self.type_2_association_dict[-21]
            else:
                return self.type_2_association_dict[-21].intersection(self.go_slim_set)

        elif function_type == "MF":
            if go_slim_or_basic == "basic":
                return self.type_2_association_dict[-22]
            else:
                return self.type_2_association_dict[-22].intersection(self.go_slim_set)

        elif function_type == "CP":
            if go_slim_or_basic == "basic":
                return self.type_2_association_dict[-23]
            else:
                return self.type_2_association_dict[-23].intersection(self.go_slim_set)
        else:
            print("function_type: '{}' does not exist".format(function_type))
            raise StopIteration

    def get_association_dict(self, protein_ans_list, gocat_upk, basic_or_slim): #, backtracking=True):
        """
        :param protein_ans_list: ListOfString
        :param gocat_upk: String (one of "GO", "UPK", "KEGG", "DOM")
        :param basic_or_slim: String (one of "basic" or "slim")
        :param backtracking: Bool (Flag to add parents of functional terms)
        :return: Dict(key: AN, val: SetOfAssociations)
        """
        an_2_functions_dict = defaultdict(lambda: set())
        if gocat_upk in {"GO", "UPK", "all_GO", "BP", "MF", "CP"}:
            association_set_2_restrict = self.get_ontology_set_of_type(gocat_upk, basic_or_slim)
        elif gocat_upk == "KEGG":
            association_set_2_restrict = self.KEGG_functions_set
        elif gocat_upk == "DOM":
            association_set_2_restrict = self.DOM_functions_set
        else:
            raise NotImplementedError
        cursor = get_cursor()
        protein_ans_list = str(protein_ans_list)[1:-1]
        sql_statement = "SELECT protein_2_function.an, protein_2_function.function FROM protein_2_function WHERE protein_2_function.an IN({});".format(protein_ans_list)
        cursor.execute(sql_statement)
        results = cursor.fetchall()
        for res in results:
            an = res[0]
            associations_list = res[1]
            an_2_functions_dict[an] = set(associations_list).intersection(association_set_2_restrict)
        cursor.close()
        # if backtracking:
        an_2_functions_dict = self.backtrack_child_terms(an_2_functions_dict, self.child_2_parent_dict)
            # for an, functions in an_2_functions_dict.items():
            #     parents_temp = set()
            #     for function_ in functions:
            #         try:
            #             parents_temp = parents_temp.union(self.child_2_parent_dict[function_])
            #         except KeyError:
            #             pass
            #     an_2_functions_dict[an] = an_2_functions_dict[an].union(parents_temp)
        return an_2_functions_dict

    # def get_association_dict_split_by_category(self, protein_ans_list): #, backtracking=True):
    #     """
    #     #!!! is speed an issue? if so restructure protein_2_function table in DB to long format !?
    #     STRING version, get all functional associations but split them by category
    #     :param protein_ans_list: ListOfString
    #     :param backtracking: Bool (Flag to add parents of functional terms)
    #     :return: Dict(key: AN, val: SetOfAssociations)
    #     """
    #     an_2_functions_dict_BP = defaultdict(lambda: set())
    #     an_2_functions_dict_CP = defaultdict(lambda: set())
    #     an_2_functions_dict_MF = defaultdict(lambda: set())
    #     an_2_functions_dict_UPK = defaultdict(lambda: set())
    #     an_2_functions_dict_KEGG = defaultdict(lambda: set())
    #     an_2_functions_dict_DOM = defaultdict(lambda: set())
    #
    #     cursor = get_cursor()
    #     protein_ans_list = str(protein_ans_list)[1:-1]
    #     sql_statement = "SELECT protein_2_function.an, protein_2_function.function FROM protein_2_function WHERE protein_2_function.an IN({});".format(protein_ans_list)
    #     cursor.execute(sql_statement)
    #     results = cursor.fetchall()
    #     for res in results:
    #         an, associations_list = res
    #         an_2_functions_dict_BP[an] = set(associations_list).intersection(self.BP_basic_functions_set)
    #         an_2_functions_dict_CP[an] = set(associations_list).intersection(self.CP_basic_functions_set)
    #         an_2_functions_dict_MF[an] = set(associations_list).intersection(self.MF_basic_functions_set)
    #         an_2_functions_dict_UPK[an] = set(associations_list).intersection(self.UPK_functions_set)
    #         an_2_functions_dict_KEGG[an] = set(associations_list).intersection(self.KEGG_functions_set)
    #         an_2_functions_dict_DOM[an] = set(associations_list).intersection(self.DOM_functions_set)
    #
    #     cursor.close()
    #     # if backtracking:
    #     an_2_functions_dict_BP = self.backtrack_child_terms(an_2_functions_dict_BP, self.child_2_parent_dict)
    #     an_2_functions_dict_CP = self.backtrack_child_terms(an_2_functions_dict_CP, self.child_2_parent_dict)
    #     an_2_functions_dict_MF = self.backtrack_child_terms(an_2_functions_dict_MF, self.child_2_parent_dict)
    #     an_2_functions_dict_UPK = self.backtrack_child_terms(an_2_functions_dict_UPK, self.child_2_parent_dict)
    #
    #     return {"BP": an_2_functions_dict_BP,
    #             "CP": an_2_functions_dict_CP,
    #             "MF": an_2_functions_dict_MF,
    #             "UPK": an_2_functions_dict_UPK,
    #             "KEGG": an_2_functions_dict_KEGG,
    #             "DOM": an_2_functions_dict_DOM}

    @staticmethod
    def get_child_2_parent_dict(direct=False, type_=None, verbose=False):
        """
        SELECT ontologies.child, ontologies.parent FROM ontologies WHERE ontologies.type='-23' AND ontologies.direct=TRUE;
        :param direct: Bool (Flag to retrieve only direct parents or not)
        :param type_: None or Integer (restrict to entity-type, e.g. -21 for GO-terms of 'Biological process'
        :param verbose: Bool (Flag to print infos)
        :return: Dictionary ( key=child (String), val=set of parents (String) )
        """
        cursor = get_cursor()
        select_statement = "SELECT ontologies.child, ontologies.parent FROM ontologies"
        extend_stmt = ""
        if type_ is not None:
            extend_stmt += " WHERE ontologies.type='{}'".format(type_)
            if direct:
                extend_stmt += " AND ontologies.direct=TRUE"
        else:
            if direct:
                extend_stmt += " WHERE ontologies.direct=TRUE"

        sql_statement = select_statement + extend_stmt + ";"
        cursor.execute(sql_statement)
        results = cursor.fetchall()
        child_2_parent_dict = {}
        if verbose:
            print(sql_statement)
            print("Number of rows fetched: ", len(results))
        for res in results:
            child, parent = res
            if child not in child_2_parent_dict:
                child_2_parent_dict[child] = {parent}
            else:
                child_2_parent_dict[child].update([parent])
        cursor.close()
        return child_2_parent_dict

    @staticmethod
    def backtrack_child_terms(an_2_functions_dict, child_2_parent_dict):
        for an, functions in an_2_functions_dict.items():
            parents_temp = set()
            for function_ in functions:
                try:
                    parents_temp = parents_temp.union(child_2_parent_dict[function_])
                except KeyError:
                    pass
            an_2_functions_dict[an] = an_2_functions_dict[an].union(parents_temp)
        return an_2_functions_dict

class PersistentQueryObject_STRING(PersistentQueryObject):
    """
    used to query protein 2 functional associations
    only protein_2_function is queried in Postgres,
    everything else is in memory but still deposited in the DB any way
    """
    def __init__(self):
        # super(PersistentQueryObject, self).__init__() # py2 and py3
        # super().__init__() # py3

        self.type_2_association_dict = self.get_type_2_association_dict()
        self.go_slim_set = self.get_go_slim_terms()
        self.KEGG_functions_set = self.get_functions_set_from_functions(function_type="KEGG")

        # ToDo not in DB yet
        # self.DOM_functions_set = self.get_functions_set_from_functions(function_type="DOM")

        ##### pre-load go_dag and goslim_dag (obo files) for speed, also filter objects
        self.upk_dag = obo_parser.GODag(obo_file=FN_KEYWORDS, upk=True)
        self.goslim_dag = obo_parser.GODag(obo_file=FN_GO_SLIM)

        # go_dag.update_association() #???
        self.go_dag = obo_parser.GODag(obo_file=FN_GO_BASIC)
        # for go_term in go_dag.keys():
        #     _ = go_dag[go_term].get_all_parents()
        #     go_dag[go_term].update_association()
        # self.go_dag = go_dag

        # for backtracking
        # self.child_2_parent_dict = self.get_child_2_parent_dict()

        self.KEGG_pseudo_dag = obo_parser.KEGG_pseudo_dag()
        # todo
        # self.DOM_pseudo_dag = obo_parser.DOM_pseudo_dag()
        self.DOM_pseudo_dag = "ToDo later since data missing"

    def get_association_dict_split_by_category(self, protein_ans_list):
        """
        backtracking is always True, since already backtracked functional associations in DB
        :param protein_ans_list: ListOfString
        :return: etype_2_association_dict(key=entity_type(String), val=Dict(key=AN(String), val=SetOfFunctions(String)))
        """
        ### key=entity_type(String), val=Dict(key=AN, val=SetOfFunctions)
        etype_2_association_dict = {"-21": {}, # | GO:0008150 | -21 | GO biological process |
                          "-22": {}, # | GO:0005575 | -22 | GO cellular component |
                          "-23": {}, # | GO:0003674 | -23 | GO molecular function |
                          "-51": {}, # UniProt keywords
                          "-52": {}, # KEGG
                          "-53": {}, # SMART
                          "-54": {}, # InterPro
                          "-55": {}, # PFAM
                          "-56": {}  # PMID
                          }

        cursor = get_cursor()
        protein_ans_list = str(protein_ans_list)[1:-1]
        sql_statement = "SELECT protein_2_function.an, protein_2_function.function, protein_2_function.etype FROM protein_2_function WHERE protein_2_function.an IN({});".format(protein_ans_list)
        cursor.execute(sql_statement)
        results = cursor.fetchall()
        for res in results:
            an, associations_list, etype = res
            etype_2_association_dict[str(etype)][an] = set(associations_list)
        # cursor.close()
        return etype_2_association_dict



def get_termAN_from_humanName_functionType(functionType, humanName):
    if humanName is None:
        return ""
    return functionType_term_2_an_dict[functionType][humanName]

def parse_result_child_parent(result):
    return set([item for sublist in result for item in sublist])

def get_taxids():
    """
    return all TaxIDs from taxid_2_proteins as sorted List of Integers
    :return: List of Integers
    """
    cursor = get_cursor()
    cursor.execute("SELECT taxid_2_protein.taxid FROM taxid_2_protein")
    records = cursor.fetchall()
    cursor.close()
    return sorted([rec for rec in records])

def get_proteins_of_taxid(taxid):
    cursor = get_cursor()
    cursor.execute("SELECT taxid_2_protein.an_array FROM taxid_2_protein WHERE taxid_2_protein.taxid={}".format(taxid))
    records = cursor.fetchall()
    cursor.close()
    return sorted(records[0])



if __name__ == "__main__":
    # import os
    # user = os.environ['POSTGRES_USER']
    # pwd = os.environ['POSTGRES_PASSWORD']
    # db = os.environ['POSTGRES_DB']
    # host = 'db'
    # port = '5432'
    # print("user", user)
    # print("pwd", pwd)
    # print("db", db)

    # cursor = get_cursor()
    # cursor = get_cursor(host=host, dbname=db, user=user, password="postgres")
    cursor = get_cursor()
    cursor.execute("SELECT * FROM functions WHERE functions.type='GO' LIMIT 5")
    cursor.execute("SELECT * FROM protein_2_function WHERE protein_2_function.an='A0A009DWB1'")
    records = cursor.fetchall()
    print(records)
    cursor.close()


    # print(get_cursor())
    # print(query_example(get_cursor()))
    # print(PersistentQueryObject())
    # pass
    # import pandas as pd
    # import tools
    # # fn = r"/Users/dblyon/modules/cpr/agotool/static/data/exampledata/exampledata_human.txt"
    # fn = r"/Users/dblyon/Downloads/1A_Data_for_web_tool_test_AbundaceCorrection_fUbi.txt"
    # df = pd.read_csv(fn, sep='\t')
    # ans_list = list(df["background"].unique())
    # ans_list = tools.commaSepCol2uniqueFlatList(df, "background", sep=";", unique=True)
    # print(len(ans_list))
    # pqo = PersistentQueryObject()
    # ### 1.)
    # protein_ans_list = ans_list # ['P62805']
    # gocat_upk = "all_GO"
    # basic_or_slim = "basic"
    # association_dict = pqo.get_association_dict(protein_ans_list, gocat_upk, basic_or_slim)
    # print(len(association_dict))
    # # ### 2.)
    # secondary_2_primary_dict = pqo.map_secondary_2_primary_ANs(ans_list)
    # # print(len(secondary_2_primary_dict))
    # # secondary_2_primary_dict = pqo.map_secondary_2_primary_ANs_v2(ans_list)
