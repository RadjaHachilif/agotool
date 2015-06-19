import cPickle as pickle
from os.path import expanduser
home = expanduser("~")


class Parser_UniProt_goa_ref(object):
    """
    formerly known as 'Goretriever'
    parse UniProt goa_ref files retrieved from ftp://ftp.ebi.ac.uk/pub/databases/GO/goa/
    # e.g. gene_association.goa_ref_yeast
    # additional info http://www.geneontology.org/doc/GO.references
    produce list of GO-terms associated with given AccessionNumber
    """
    go_parents_name2num_dict = {"BP": "GO:0008150", "CP": "GO:0005575", "MF": "GO:0003674"}

    def __init__(self, goa_ref_fn=None):
        """
        :return: None
        """
        self.an2go_dict = {} # key=AccessionNumber val=ListOfStrings (GO-terms)
        self.date = "not set yet" # generation date
        self.obolibrary = "not yet set" # link to obo-library
        if not goa_ref_fn:
            goa_ref_fn = home + r'/CloudStation/CPR/Brian_GO/go_rescources/UniProt_goa/yeast/gene_association.goa_ref_yeast'
        self.parse_goa_ref(goa_ref_fn)

    def parse_goa_ref(self, fn):
        """
        parse UniProt goa_ref file filling self.an2go_dict
        :param fn: raw String
        :return: None
        """
        fh = open(fn, "r")
        for line in fh:
            if line[0] == "!":
                if line[0:11] == "!Generated:":
                    self.date = line.replace("!Generated:", "").strip()
                elif line[0:12] == "!GO-version:":
                    self.obolibrary = line.replace("!GO-version:", "").strip()
            else:
                line_split = line.split("\t")
                if len(line_split) == 17:
                    an = line_split[1] # DB_Object_ID
                    goid = line_split[4] # GO_ID
                    if not self.an2go_dict.has_key(an):
                        self.an2go_dict[an] = [goid]
                    else:
                        self.an2go_dict[an].append(goid)
        self.remove_redundant_go_terms()
        fh.close()

    def parse_goa_ref_v2(self, fn):
        """
        parse UniProt goa_ref file filling self.an2go_dict
        an2go_dict: key=AN, val=set(GO-terms)
        :param fn: raw String
        :return: None
        """
        fh = open(fn, "r")
        for line in fh:
            if line[0] == "!":
                if line[0:11] == "!Generated:":
                    self.date = line.replace("!Generated:", "").strip()
                elif line[0:12] == "!GO-version:":
                    self.obolibrary = line.replace("!GO-version:", "").strip()
            else:
                line_split = line.split("\t")
                if len(line_split) == 17:
                    an = line_split[1] # DB_Object_ID
                    goid = line_split[4] # GO_ID
                    if not self.an2go_dict.has_key(an):
                        self.an2go_dict[an] = set([goid])
                    else:
                        self.an2go_dict[an].update([goid])
        self.set2sortedlist()
        fh.close()

    def set2sortedlist(self):
        for an in self.an2go_dict.keys():
            self.an2go_dict[an] = sorted(self.an2go_dict[an])

    def get_goterms_from_an(self, an):
        """
        produce list of GO-terms associated with given AccessionNumber
        :param an: String
        :return: ListOfString
        """
        try:
            return self.an2go_dict[an]
        except KeyError:
            return -1 #!!!

    def get_goterms_from_an_limit2parent(self, an, go_parent, obo_dag):
        '''
        produce list of GO-terms associated with given AccessionNumber
        limit to child terms of given parent
        :param an: String
        :param go_parent: String
        :param obo_dag: GODag Instance
        :return: ListOfString
        '''
        goterms_list = self.get_goterms_from_an(an)
        if goterms_list == -1:
            return -1
        else:
            goterms_of_parent = []
            for goterm in goterms_list:
                if obo_dag[goterm].has_parent(self.go_parents_name2num_dict[go_parent]):
                    goterms_of_parent.append(goterm)
        if len(goterms_of_parent) >= 1:
            return goterms_of_parent
        else:
            return -1

    def get_ans(self):
        '''
        produce List of AccessionNumbers
        :return: ListOfString
        '''
        return sorted(self.an2go_dict)

    def get_date(self):
        """
        produce generation date of UniProt resource file
        :return: String
        """
        return self.date

    def get_obolibrary(self):
        """
        produce link to obo-library
        :return: String
        """
        return self.obolibrary

    def remove_redundant_go_terms(self):
        """
        remove redundant go-terms for each AccessionNumber if present
        and sort list of go-terms
        :return: None
        """
        for an in self.an2go_dict.keys():
            self.an2go_dict[an] = sorted(set(self.an2go_dict[an]))

    def pickle(self, fn_p):
        """
        pickle relevant attributes to given FileName
        :param fn_p: raw String
        :return: None
        """
        dict2pickle = {}
        dict2pickle["an2godict"] = self.an2go_dict
        dict2pickle["date"] = self.date
        dict2pickle["obolibrary"] = self.obolibrary
        pickle.dump(dict2pickle, open(fn_p, "wb"))
        del dict2pickle

    def unpickle(self, fn_p):
        """
        unpickle and set relevant attributes to instance
        :param fn_p: raw String
        :return: None
        """
        dict2pickle = pickle.load(open(fn_p, "rb"))
        self.an2go_dict = dict2pickle["an2godict"]
        self.date = dict2pickle["date"]
        self.obolibrary = dict2pickle["obolibrary"]
        del dict2pickle

    def write_association2file(self, fn_out):
        '''
        produce input file for goatools termed 'association'
        containing all AccessionNumbers of theoretical proteome and
        their corresponding GO-IDs
        e.g.:
        AN tab GO-id1;GO-id2;GO-id3
        ACD5	GO:0005575;GO:0003674;GO:0008219
        :param fn_out: rawString
        :return: None
        '''
        with open(fn_out, 'w') as fh_out:
            for an in self.get_ans():
                go_list = self.get_goterms_from_an(an)
                if go_list == -1:
                    pass # #!!! should there be a default value instead?
                else:
                    fh_out.write(an + '\t' + ';'.join(go_list) + '\n')

    def get_association_dict(self, go_parent, obo_dag):
        '''
        produce association_dictionary, containing all AccessionNumbers of theoretical proteome and
        their corresponding GO-IDs (most specific ones)
        do not report GO-ID without association
        assoc is a dict: key=AN, val=set of go-terms
        go_parten is one of: 'MF', 'BP', 'CP', "all_GO"
        limit the set of GO-terms to the given parent category
        obo_dag is a Dict: key=GO-term, val=GOTerm instance
        can be queried for parent term: obo_dag['GO:1990413'].has_parent('GO:0008150')
        # "BP" "GO:0008150"
        # "CP" "GO:0005575"
        # "MF" "GO:0003674"
        :param go_parent: String
        :param obo_dag: GODag Instance
        :return: Dict
        '''
        assoc_dict = {}
        for an in self.get_ans():
            if not assoc_dict.has_key(an):
                if go_parent == "all_GO":
                    goterms_list = self.get_goterms_from_an(an)
                else:
                    goterms_list = self.get_goterms_from_an_limit2parent(an, go_parent, obo_dag)
                if goterms_list != -1:
                    assoc_dict[an] = set(goterms_list)
            else:
                if go_parent == "all_GO":
                    goterms_set = set(self.get_goterms_from_an(an))
                else:
                    goterms_set = set(self.get_goterms_from_an_limit2parent(an, go_parent, obo_dag))
                if assoc_dict[an] != goterms_set:
                    print('Associations-dict: multiple entries of AN with diverging associations:')
                    print(an + ' ' + self.get_goterms_from_an(an))
        return assoc_dict


