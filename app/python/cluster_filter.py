import pandas as pd
import numpy as np
import itertools
import shlex
import subprocess
import os, sys
import threading
import signal
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.realpath(__file__))))
import variables


class TimeOutException(BaseException):
    pass

# filename = '{}.pid'.format(os.getpid())
# filename = '{}_pid'.format(os.getpid())

class MCL(object):

    def __init__(self, SESSION_FOLDER_ABSOLUTE, max_timeout):
        # self.set_fh_log(os.path.dirname(os.getcwd()) + r'/data/mcl/mcl_log.txt')
        # self.abs_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) + r'/data/mcl/'
        # self.set_fh_log(self.abs_path + 'mcl_log.txt')
        self.abs_path = SESSION_FOLDER_ABSOLUTE
        self.set_fh_log(os.path.join(self.abs_path, 'mcl_log.txt'))
        self.max_timeout = max_timeout * 60
        # print("#"*80)
        # print("2. max_timeout {}".format(max_timeout))

    def set_fh_log(self, log_fn):
        self.fh_log = open(log_fn, "a")

    def get_fh_log(self):
        return self.fh_log

    def close_log(self):
        # self.get_fh_log().flush()
        self.get_fh_log().close()

    def jaccard_index_ans_setA2B(self, ans_set1, ans_set2):
        # ABC = len(ans_set1.union(ans_set2))
        ABC = len(ans_set1 & ans_set2)
        # try:
        #     return B/ABC
        # except ZeroDivisionError:
        #     return 0.0
        if ABC == 0:
            return 0.0
        else:
            # B = float(len(ans_set1.intersection(ans_set2)))
            B = float(len(ans_set1 | ans_set2))
            return B / ABC

    def write_JaccardIndexMatrix(self, fn_results, fn_out): #!!! profile this function
        """
        expects a DataFrame with a 'ANs_foreground' column,
        calculates the Jaccard Index for all
        combinations of AN sets.
        :param fn_results: String
        :param fn_out: rawString
        :return: None
        """
        df = pd.read_csv(fn_results, sep='\t')
        func = lambda x: set(x.split(", "))
        df["ANs_foreground_set"] = map(func, df["ANs_foreground"])
        index_of_col = df.columns.tolist().index("ANs_foreground_set")
        df_ans_foreground_set = df.values[:, index_of_col]
        with open(fn_out, 'w') as fh:
            for combi in itertools.combinations(df.index, 2):
                c1, c2 = combi
                ans_set1 = df_ans_foreground_set[c1]
                ans_set2 = df_ans_foreground_set[c2]
                ji = self.jaccard_index_ans_setA2B(ans_set1, ans_set2)
                line2write = str(c1) + '\t' + str(c2) + '\t' + str(ji) + '\n'
                fh.write(line2write)

    def results2list_of_sets(self, fn_results):
        with open(fn_results, 'r') as fh:
            lines_split = [ele.strip().split('\t') for ele in fh]
        ANs_foreground_index = lines_split[0].index("ANs_foreground")
        return [set(row[ANs_foreground_index].split(', ')) for row in lines_split[1:]]

    def write_JaccardIndexMatrix_speed(self, fn_results, fn_out):
        list_of_sets = self.results2list_of_sets(fn_results)
        with open(fn_out, 'w') as fh:
            for combi in itertools.combinations(range(0, len(list_of_sets)), 2):
                c1, c2 = combi
                ans_set1 = list_of_sets[c1]
                ans_set2 = list_of_sets[c2]
                ABC = len(ans_set1 & ans_set2)
                if ABC == 0:
                    ji = 0.0
                else:
                    B = len(ans_set1 | ans_set2) * 1.0
                    ji = B / ABC
                line2write = str(c1) + '\t' + str(c2) + '\t' + str(ji) + '\n'
                fh.write(line2write)

    def mcl_cluster2file(self, mcl_in, inflation_factor, mcl_out):
        # print("MCL max_timeout:", self.max_timeout)
        # cmd_text = """mcl %s -I %d --abc -o %s""" % (mcl_in, inflation_factor, mcl_out)
        cmd_text = """mcl {} -I {} --abc -o {}""".format(mcl_in, inflation_factor, mcl_out)
        # print("#"*80)
        # print("MCL: ", cmd_text)
        # print("#" * 80)
        args = shlex.split(cmd_text)
        #ph = subprocess.Popen(args, stdin=None, stdout=self.get_fh_log(), stderr=self.get_fh_log())
#        self.pid = ph.pid
        class my_process(object):
            # hack to get a namespace
            def open(self, args, **kwargs):
                ph = subprocess.Popen(args, **kwargs)
                self.process = ph
                self.pid = ph.pid
                ph.wait()
        kwargs = {"stdin" : None,
                  "stdout" : self.get_fh_log(),
                  "stderr" : self.get_fh_log()}
        p = my_process()
        t = threading.Thread(target=p.open, args=(args,), kwargs=kwargs)
        t.start()
        self.get_fh_log().flush()
        # wait for max_time, kill or return depending on time
#        is_alive = False
        for time_passed in range(1, self.max_timeout + 1):
            time.sleep(1)
            if not t.isAlive():
                break
        if t.isAlive():
            os.kill(p.pid, signal.SIGKILL)
            raise TimeOutException("MCL took too long and was killed:")
        ###################################################################### --> I like you <3
        ########## in python 3 Popen.wait takes 1 argument          ##########
        ########## ... the name is timeout... guess what it does    ########## ^^ this is my favorite smiley <3
        ########## ... ever considered switching to python 3 ;)     ##########
        ######################################################################
#        return ph.wait();

    def get_clusters(self, mcl_out):
        """
        parse MCL output
        returns nested list of integers
        [
        [1, 3, 4],
        [2, 5]
        ]
        :param mcl_out: rawFile
        :return: ListOfListOfIntegers
        """
        cluster_list = []
        with open(mcl_out, 'r') as fh:
            for line in fh:
                cluster_list.append([int(ele) for ele in line.strip().split('\t')])
        return cluster_list

    def calc_MCL_get_clusters(self, session_id, fn_results, inflation_factor):
        mcl_in = os.path.join(self.abs_path, 'mcl_in') + session_id + '.txt'
        mcl_out = os.path.join(self.abs_path, 'mcl_out') + session_id + '.txt'
        if not os.path.isfile(mcl_in):
            self.write_JaccardIndexMatrix_speed(fn_results, mcl_in)
        self.mcl_cluster2file(mcl_in, inflation_factor, mcl_out)
        self.close_log()
        return self.get_clusters(mcl_out)

def filter_parents_if_same_foreground_v4(df_orig, lineage_dict, blacklisted_terms, entity_types_with_ontology):
    blacklisted_terms = set(blacklisted_terms).copy()
    cond_df_2_filter = df_orig["etype"].isin(entity_types_with_ontology)
    df = df_orig[cond_df_2_filter]
    df_no_filter = df_orig[~cond_df_2_filter]
    terms_reduced = []
    for name, group in df.groupby("foreground_ids"):
        for term in group.sort_values(["hierarchical_level", "p_value", "foreground_count"], ascending=[False, True, False])["term"].values:
            if not term in blacklisted_terms:
                terms_reduced.append(term)
                blacklisted_terms = blacklisted_terms.union(lineage_dict[term])
    df = df[df["term"].isin(terms_reduced)]
    # add df_orig part that can't be filtered due to missing ontology
    return pd.concat([df, df_no_filter], sort=False)

def get_header_results(fn):
        results = []
        with open(fn, 'r') as fh:
            for line in fh:
                res2append = line.strip().split('\t')
                if len(res2append) > 1:
                    results.append(res2append)
        header = results[0]
        results = results[1:]
        return header, results


if __name__ == "__main__":
    ############################################################################
    ##### PROFILING MCL
    # data=GO-terms yeast default
    SESSION_FOLDER_ABSOLUTE = r'/Users/dblyon/modules/cpr/agotool/static/data/session/'
    mcl = MCL(SESSION_FOLDER_ABSOLUTE, max_timeout=1)
    # session_id = "_5581_1438333013.92"
    # session_id = '_6027_1440960988.55'
    # session_id = '_6029_1440960996.93'
    session_id = '_31830_1447841531.11'
    # results_orig_31830_1447841531.11.tsv
    inflation_factor = 2.0
    fn_results_orig_absolute = os.path.join(SESSION_FOLDER_ABSOLUTE, ("results_orig" + session_id + ".tsv"))
    cluster_list = mcl.calc_MCL_get_clusters(session_id, fn_results_orig_absolute, inflation_factor)
    ############################################################################
# A4D212 no description
# A4D212

    # mcl = MCL_no_input_file_pid()
    # header, results = get_header_results(r'/Users/dblyon/modules/cpr/goterm/agotool/static/data/mcl/MCL_test.txt')
    # cluster_list = mcl.calc_MCL_get_clusters(header, results, inflation_factor=2.0)
    # print cluster_list

    # fn = r'/Users/dblyon/modules/cpr/goterm/mcl/Yeast_Acetyl_vs_AbCorr_UPK.txt'
    # mcl_in = 'mcl_in.txt'
    # df = pd.read_csv(fn, sep='\t')
    # mcl = MCL()
    # mcl.write_JaccardIndexMatrix(df, mcl_in)
    # mcl_out = mcl_in.replace('_in.txt', '_out.txt')
    # inflation_factor = 2.0
    # mcl.mcl_cluster2file(mcl_in, inflation_factor, mcl_out)
    # cluster_list = mcl.get_clusters(mcl_out)

    # fn = r'/Users/dblyon/modules/cpr/goterm/mcl/Yeast_Acetyl_vs_AbCorr_UPK.txt'
    # mcl = MCL()
    # cluster_list = mcl.calc_MCL_get_clusters(fn, inflation_factor=2.0)
