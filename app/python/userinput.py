import pandas as pd
import sys, os
import numpy as np
from collections import defaultdict
from io import StringIO # from StringIO import StringIO
from itertools import zip_longest # from itertools import izip_longest
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.realpath(__file__))))
import tools #, query

pd.options.mode.chained_assignment = None

# ToDo check if values need to be sorted for both input types (classes)


DEFAULT_MISSING_BIN = -1


class Userinput:
    """
    expects 2 arrays,
    foregroundfreq: Pandas DataFrame 1column
    backgrndfreq: 2D array/Pandas DataFrame, with backgrnd_an, backgrnd_int

    enrichment_method is one of: "abundance_correction", "compare_samples", "compare_groups", "characterize_foreground"
     - abundance_correction: Foreground vs Background abundance corrected
     - compare_samples: Foreground vs Background (no abundance correction)
     - compare_groups: Foreground(replicates) vs Background(replicates), --> foreground_n and background_n need to be set
     - characterize_foreground: Foreground only
    """
    def __init__(self, pqo, fn=None, foreground_string=None, background_string=None,
            col_foreground='foreground', col_background='background', col_intensity='intensity',
            num_bins=100, decimal='.', enrichment_method="abundance_correction", foreground_n=None, background_n=None):
        self.pqo = pqo
        self.fn = fn
        self.foreground_string = foreground_string
        self.background_string = background_string
        self.decimal = decimal
        self.num_bins = num_bins
        self.col_foreground = col_foreground
        self.col_background = col_background
        self.col_intensity = col_intensity
        self.enrichment_method = enrichment_method
        self.foreground_n = foreground_n
        self.background_n = background_n
        self.df_orig, self.decimal, self.check_parse = self.parse_input()
        if self.check_parse:
            self.foreground, self.background, self.check_cleanup = self.cleanupforanalysis(self.df_orig, self.col_foreground, self.col_background, self.col_intensity)
        else:
            self.check_cleanup = False

    def parse_input(self):
        if self.fn is None: # use copy & paste field
            self.fn = StringIO()
            self.foreground_string = self.remove_header_if_present(self.foreground_string.replace("\r\n", "\n"), "foreground")
            if self.enrichment_method != "characterize_foreground":
                self.background_string = self.remove_header_if_present(self.background_string.replace("\r\n", "\n"), "background")
            is_abundance_correction = self.fast_check_is_abundance_correction(self.background_string)
            if is_abundance_correction:
                header = 'foreground\tbackground\tintensity\n'
            elif self.enrichment_method in {"compare_samples", "compare_groups"}:
                header = 'foreground\tbackground\n'
            elif self.enrichment_method == "characterize_foreground":
                header = 'foreground\n'
            else:
                raise StopIteration
            self.fn.write(header)
            if self.enrichment_method != "characterize_foreground":
                for a, b in zip_longest(self.foreground_string.split("\n"), self.background_string.split("\n"), fillvalue="\t"):
                    self.fn.write(a.strip() + "\t" + b.strip() + "\n")
            else:
                self.fn.write(self.foreground_string)
            self.fn.seek(0)
        try:
            df_orig, decimal, check_parse = self.check_decimal(self.fn)
        except FileNotFoundError:
            return None, ".", False
        return df_orig, decimal, check_parse

    def cleanupforanalysis(self, df, col_foreground, col_background, col_intensity):
        check_cleanup = True
        self.background = None

        ### remove rows consisting of only NaNs
        df = df[-df.isnull().all(axis=1)]

        ### remove NaNs from foregroundfrequency and backgroundfrequency AN-cols
        self.foreground = df.loc[pd.notnull(df[col_foreground]), [col_foreground]]
        if self.enrichment_method == "abundance_correction": # abundance_correction
            # self.background = df.loc[pd.notnull(df[col_background]), [col_background, col_intensity]]
            self.background = df[[col_background, col_intensity]]
            # set default missing value for NaNs
            self.background.loc[pd.isnull(df[col_background]), col_intensity] = DEFAULT_MISSING_BIN
        elif self.enrichment_method in {"compare_samples", "compare_groups"}: # elif self.enrichment_method != "characterize_foreground":
            self.background = df.loc[pd.notnull(df[col_background]), [col_background]]
        else:
            pass

        ### remove splice variant appendix and drop duplicates
        try:
            self.foreground[col_foreground] = self.foreground[col_foreground].apply(self.remove_spliceVariant)
        except AttributeError: # np.nan can't be split
            return self.foreground, self.background, False
        #if self.enrichment_method in {"abundance_correction", "compare_samples", "characterize_foreground"}:
        if self.enrichment_method != "compare_groups": # abundance_correction
            self.foreground.drop_duplicates(subset=col_foreground, inplace=True)
        self.foreground.index = range(0, len(self.foreground))
        if self.enrichment_method != "characterize_foreground": # abundance_correction
            try:
                self.background[col_background] = self.background[col_background].apply(self.remove_spliceVariant)
            except AttributeError:
                return self.foreground, self.background, False
            self.background = self.background.drop_duplicates(subset=col_background)

        ### map abundance from background to foreground, set default missing value for NaNs
        if self.enrichment_method == "abundance_correction":
            cond = pd.isnull(self.background[col_intensity])
            self.background.loc[cond, col_intensity] = DEFAULT_MISSING_BIN
            an_2_intensity_dict = self.create_an_2_intensity_dict(zip(self.background[col_background], self.background[col_intensity]))
            self.foreground["intensity"] = self.map_intensities_2_foreground(self.foreground[col_foreground], an_2_intensity_dict )

        ### map obsolete Accessions to primary ANs, by replacing secondary ANs with primary ANs
        secondary_2_primary_dict = self.pqo.map_secondary_2_primary_ANs(self.get_all_unique_ANs())
        self.foreground[col_foreground] = self.foreground[col_foreground].apply(self.replace_secondary_with_primary_ANs, args=(secondary_2_primary_dict,))
        if self.enrichment_method != "characterize_foreground":
            self.background[col_background] = self.background[col_background].copy().apply(self.replace_secondary_with_primary_ANs, args=(secondary_2_primary_dict,))

        ### sort values for iter bins
        if self.enrichment_method == "abundance_correction":
            cond = self.foreground["intensity"] > DEFAULT_MISSING_BIN
            if sum(cond) == 0:  # render info_check_input.html
                check_cleanup = False
            self.foreground = self.foreground.sort_values(["intensity", "foreground"])
            self.background = self.background.sort_values(["intensity", "background"])

        return self.foreground, self.background, check_cleanup

    def check_decimal(self, fn):
        """
        test if userinput uses ',' or '.' as a decimal separator
        and if 3 columns for abundance_correction exist
        return df attribute, and set check_parse to False
        :param fn: FileName
        :return: (DF_orig, Decimal(a String), check_parse(a Boolean))
        """
        decimal = '.'
        check_parse = False
        df_orig = None

        try:
            df_orig = pd.read_csv(fn, sep='\t', decimal=decimal)
            check_parse = True
        except pd.errors.ParserError:
            return df_orig, decimal, check_parse

        if self.enrichment_method == "abundance_correction":
            df_orig = self.change_column_names(df_orig)
            if len({self.col_background, self.col_intensity, self.col_foreground}.intersection(set(df_orig.columns.tolist()))) == 3:
                try:
                    np.histogram(df_orig.loc[pd.notnull(df_orig[self.col_intensity]), self.col_intensity], bins=10)
                    check_parse = True
                except TypeError:
                    try:
                        decimal = ','
                        df_orig = pd.read_csv(fn, sep='\t', decimal=decimal)
                        np.histogram(df_orig.loc[pd.notnull(df_orig[self.col_intensity]), self.col_intensity], bins=10)
                        check_parse = True
                    except TypeError:
                        pass
        return df_orig, decimal, check_parse

    @staticmethod
    def remove_header_if_present(input_string, foreground_or_background):
        if foreground_or_background == "foreground":
            if input_string.split("\n")[0].lower() == "foreground":
                return "\n".join(input_string.split("\n")[1:])
        else:
            if input_string.split("\n")[0].lower() == "background\tintensity":
                return "\n".join(input_string.split("\n")[1:])
        return input_string

    @staticmethod
    def fast_check_is_abundance_correction(background_string):
        try:
            string_split = background_string.split("\n", 1)[0].split("\t")
        except AttributeError:
            return False
        try:
            float(string_split[1])
        except (IndexError, ValueError) as _:
            return False
        return True

    @staticmethod
    def change_column_names(df):
        """
        :param df: Pandas DataFrame
        :return: Pandas DataFrame
        """
        cols = sorted(df.columns.tolist())
        cols = [colname.lower() for colname in cols]
        if "population" in cols:
            df = df.rename(columns={"population": "background"})
        if "population_an" in cols:
            df = df.rename(columns={"population_an": "background"})
        if "population_int" in cols:
            df = df.rename(columns={"population_int": "intensity"})
        if "sample" in cols:
            df = df.rename(columns={"sample": "foreground"})
        if "sample_an" in cols:
            df = df.rename(columns={"sample_an": "foreground"})
        return df

    @staticmethod
    def replace_secondary_with_primary_ANs(ans_string, secondary_2_primary_dict):
        ans_2_return = []
        for an in ans_string.split(";"): # if proteinGroup
            if an in secondary_2_primary_dict:
                ans_2_return.append(secondary_2_primary_dict[an])
            else:
                ans_2_return.append(an)
        return ";".join(ans_2_return)

    @staticmethod
    def create_an_2_intensity_dict(list_of_tuples):
        """
        notnull values are assigned a default of -1, in order to count them in an extra bin
        e.g.
        [('P00330', '10,6690378'),
         ('P02407;P14127', '10,64061061'),
         ...]
        --> an_2_intensity_dict["P02407"] = 10,64061061
        :param list_of_tuples: ListOfTuples(ANs_string, Intensity_float)
        :return: Dict (key=AN, val=Float)
        """
        an_2_intensity_dict = defaultdict(lambda: DEFAULT_MISSING_BIN)
        for ans, int_ in list_of_tuples:
            for an in ans.split(";"):
                an_2_intensity_dict[an] = int_
        return an_2_intensity_dict

    @staticmethod
    def remove_spliceVariant(string_):
        """
        removes appendix for splice variants from accession numbers and sorts protein groups
        :param string_: String
        :return: String
        """
        return ";".join(sorted([ele.split("-")[0] for ele in string_.split(";")]))

    @staticmethod
    def map_intensities_2_foreground(foreground_series, an_2_intensity_dict):
        """
        foreground proteinGroups with abundance data
        first AN in proteinGroup used to lookup abundance values from background
        :return: Series
        """
        # foreground proteinGroups with intensities
        intensity_foreground = []
        for proteinGroup in foreground_series:
            an_first_in_proteinGroup = proteinGroup.split(";")[0]
            intensity_foreground.append(an_2_intensity_dict[an_first_in_proteinGroup])
        return pd.Series(intensity_foreground, name="intensity")

    def get_foreground_an_set(self):
        return set(self.foreground[self.col_foreground].tolist())

    def get_background_an_set(self):
        return set(self.background[self.col_background].tolist())

    def get_an_redundant_foreground(self):
        return self.foreground[self.col_foreground].tolist()

    def get_an_redundant_background(self):
        return self.background[self.col_background].tolist()

    def get_foreground_n(self):
        """
        "abundance_correction", "compare_samples", "enrichment_method", "characterize_foreground"
        :return: Int
        """
        if self.enrichment_method == "abundance_correction":
            return len(self.foreground)
        elif self.enrichment_method == "compare_samples": # no abundance correction
            return len(self.foreground)
        elif self.enrichment_method == "compare_groups": # redundancies within group, therefore n set by user
            return self.foreground_n
        elif self.enrichment_method == "characterize_foreground":
            return len(self.foreground)
        else:
            raise StopIteration # DEBUG, case should not happen

    def get_background_n(self):
        """
        "abundance_correction", "compare_samples", "compare_groups", "characterize_foreground"
        :return: Int
        """
        if self.enrichment_method == "abundance_correction": # same as foreground
            return len(self.foreground)
        elif self.enrichment_method == "compare_samples": # simply background to compare to
            return len(self.background)
        elif self.enrichment_method == "compare_groups": # redundancies within group, therefore n set by user
            return self.background_n
        elif self.enrichment_method == "characterize_foreground": # only for foreground, not background
            return None
        else:
            raise StopIteration # DEBUG, case should not happen

    def get_sample_an(self):
        return self.foreground[self.col_foreground].tolist()

    # deprecated
    def iter_bins_old(self):
        """
        map foreground proteinGroups to background abundance values,
        split foreground proteinGroups into bins based on abundance,
        calculate a correction factor for each bin (num proteinGroups foreground / num proteinGroups background),
        yield background proteinGroups and correction factor for each bin
        :return: Tuple(ListOfString(';' sep ANs), correction factor)
        """
        cond = self.foreground["intensity"] > DEFAULT_MISSING_BIN
        bins = pd.cut(self.foreground.loc[cond, "intensity"], bins=self.num_bins, retbins=True)[1]
        # bins = [DEFAULT_MISSING_BIN - 1] + list(bins) # ToDo investigate and fix
        # print(self.foreground.head())
        groups_fg = self.foreground.groupby(pd.cut(self.foreground["intensity"], bins=bins))
        groups_bg = self.background.groupby(pd.cut(self.background[self.col_intensity], bins=bins))
        for group_fg, group_bg in zip(groups_fg, groups_bg):
            # bins_fg = group_fg[0]
            # bins_bg = group_bg[0]
            # assert bins_fg == bins_bg
            proteinGroups_foreground = group_fg[1][self.col_foreground]
            proteinGroups_background = group_bg[1][self.col_background]
            len_proteinGroups_foreground = len(proteinGroups_foreground) * 1.0
            len_proteinGroups_background = len(proteinGroups_background) * 1.0
            try:
                correction_factor = len_proteinGroups_foreground / len_proteinGroups_background
            except ZeroDivisionError:
                # since the foreground is assumed to be a proper subset of the background, anything in the foreground must also be in the background
                correction_factor = 1
                proteinGroups_background = proteinGroups_foreground
            if len_proteinGroups_foreground == 0:
                continue
            # yield proteinGroups_background.tolist(), proteinGroups_foreground.tolist(), correction_factor, bins_fg
            yield proteinGroups_background.tolist(), correction_factor

    # deprecated
    @staticmethod
    def iter_bins_static(foreground, background, DEFAULT_MISSING_BIN=-1, num_bins=100):
        """
        map foreground proteinGroups to background abundance values,
        split foreground proteinGroups into bins based on abundance,
        calculate a correction factor for each bin (num proteinGroups foreground / num proteinGroups background),
        yield background proteinGroups and correction factor for each bin
        :param foreground: DataFrame(foreground(string), intensity(float))
        :param background: DataFrame(background(string), intensity(float))
        :param DEFAULT_MISSING_BIN: Float or Int
        :param num_bins: Int
        :return: Tuple(ListOfString(';' sep ANs), correction factor)
        """
        # take subset of foreground with proper abundance values and create bins
        cond = foreground["intensity"] > DEFAULT_MISSING_BIN
        bins = pd.cut(foreground.loc[cond, "intensity"], bins=num_bins, retbins=True)[1]
        # add missing bin for the remainder of proteins
        bins = np.insert(bins, 0, DEFAULT_MISSING_BIN - 1)  # bins = [DEFAULT_MISSING_BIN - 1] + list(bins)
        # cut foreground and background into bins
        groups_fg = foreground.groupby(pd.cut(foreground["intensity"], bins=bins))
        groups_bg = background.groupby(pd.cut(background["intensity"], bins=bins))
        for group_fg, group_bg in zip(groups_fg, groups_bg):
            proteinGroups_foreground = group_fg[1]["foreground"]
            proteinGroups_background = group_bg[1]["background"]
            len_proteinGroups_foreground = len(proteinGroups_foreground) * 1.0
            len_proteinGroups_background = len(proteinGroups_background) * 1.0
            try:
                correction_factor = len_proteinGroups_foreground / len_proteinGroups_background
            except ZeroDivisionError:
                # since the foreground is assumed to be a proper subset of the background, anything in the foreground must also be in the background
                correction_factor = 1
                proteinGroups_background = proteinGroups_foreground
            if len_proteinGroups_foreground == 0:
                continue
            yield proteinGroups_background.tolist(), correction_factor

    def iter_bins(self):
        """
        map foreground proteinGroups to background abundance values,
        split foreground proteinGroups into bins based on abundance,
        calculate a correction factor for each bin (num proteinGroups foreground / num proteinGroups background),
        yield background proteinGroups and correction factor for each bin
        :return: Tuple(ListOfString(';' sep ANs), correction factor)
        """
        # take subset of foreground with proper abundance values and create bins
        cond = self.foreground["intensity"] > DEFAULT_MISSING_BIN
        bins = pd.cut(self.foreground.loc[cond, "intensity"], bins=self.num_bins, retbins=True)[1]
        # add missing bin for the remainder of proteins
        bins = np.insert(bins, 0, DEFAULT_MISSING_BIN - 1)  # bins = [DEFAULT_MISSING_BIN - 1] + list(bins)
        # cut foreground and background into bins
        groups_fg = self.foreground.groupby(pd.cut(self.foreground["intensity"], bins=bins))
        groups_bg = self.background.groupby(pd.cut(self.background["intensity"], bins=bins))
        for group_fg, group_bg in zip(groups_fg, groups_bg):
            proteinGroups_foreground = group_fg[1]["foreground"]
            proteinGroups_background = group_bg[1]["background"]
            len_proteinGroups_foreground = len(proteinGroups_foreground) * 1.0
            len_proteinGroups_background = len(proteinGroups_background) * 1.0
            try:
                correction_factor = len_proteinGroups_foreground / len_proteinGroups_background
            except ZeroDivisionError:
                # since the foreground is assumed to be a proper subset of the background, anything in the foreground must also be in the background
                correction_factor = 1
                proteinGroups_background = proteinGroups_foreground
            if len_proteinGroups_foreground == 0:
                continue
            yield proteinGroups_background.tolist(), correction_factor

    def get_all_unique_ANs(self):
        """
        return all unique AccessionNumber provided by the user
        :return: ListOfString
        """
        ans = tools.commaSepCol2uniqueFlatList(self.foreground, self.col_foreground, sep=";", unique=True)
        if self.enrichment_method != "characterize_foreground":
            ans += tools.commaSepCol2uniqueFlatList(self.background, self.col_background, sep=";", unique=True)
        return list(set(ans))

    def get_all_unique_proteinGroups(self):
        proteinGroup_list = []
        proteinGroup_list += self.foreground[self.col_foreground].tolist()
        if self.enrichment_method != "characterize_foreground":
            proteinGroup_list += self.background[self.col_background].tolist()
        return list(set(proteinGroup_list))


class REST_API_input(Userinput):

    def __init__(self, pqo,
            foreground_string=None, background_string=None, background_intensity=None,
            num_bins=100, enrichment_method="abundance_correction", foreground_n=None, background_n=None):
        self.pqo = pqo
        self.df_orig = pd.DataFrame()
        self.foreground_string = foreground_string
        self.background_string = background_string
        self.background_intensity = background_intensity
        self.decimal = "."
        self.num_bins = num_bins
        self.col_foreground = "foreground"
        self.col_background = "background"
        self.col_intensity = "intensity"
        self.enrichment_method = enrichment_method
        self.foreground_n = foreground_n
        self.background_n = background_n
        self.df_orig = self.parse_input()
        self.foreground, self.background, self.check = self.cleanupforanalysis(self.df_orig, self.col_foreground, self.col_background, self.col_intensity)

    def parse_input(self):
        df_orig = pd.DataFrame()
        if self.background_string is not None:
            df_orig["background"] = pd.Series(self._replace_and_split(self.background_string))
        if self.background_intensity is not None:
            if "." in self.background_intensity:
                pass
            elif "," in self.background_intensity:
                self.decimal = ","
                # replace comma with dot, work with consistently the same DF, but report the results to the user using the their settings
                self.background_intensity = self.background_intensity.replace(",", ".")
            else: # other checks could be done, but is this really necessary?
                raise StopIteration
            df_orig["intensity"] = pd.Series(self._replace_and_split(self.background_intensity), dtype=float)
        # statement need to be here rather than at top of function in order to not cut off the Series at the length of the existing Series in the DF
        df_orig["foreground"] = pd.Series(self._replace_and_split(self.foreground_string))
        return df_orig

    @staticmethod
    def _replace_and_split(string_):
        return string_.replace("\r", "%0d").split("%0d")


if __name__ == "__main__":
    # # fn = r'/Users/dblyon/modules/cpr/metaprot/Perio_vs_CH_Bacteria.txt'
    # # fn = r'/Users/dblyon/modules/cpr/metaprot/CompareGroups_test.txt'
    # # fn = r'/Users/dblyon/modules/cpr/metaprot/test/GOenrichment_characterize_study_test_DF_proteinGroups.txt'
    # # foreground_n = 10.0
    # # background_n = 20.0
    # # proteinGroup = True
    # # ui = UserInput_compare_groups(proteinGroup, fn, foreground_n, background_n)
    # # foreground_an = ui.get_foreground_an()
    # # # backgound_an = ui.get_background_an()
    # # all_unique_an = ui.get_all_unique_ans()
    # # # print len(foreground_an), len(backgound_an), len(all_unique_an)
    # # print len(foreground_an), len(all_unique_an)
    # fn = r"/Users/dblyon/modules/cpr/agotool/static/data/exampledata/exampledata_yeast_Foreground_Background.txt"
    # fn = r"/Users/dblyon/modules/cpr/agotool/static/data/exampledata/exampledata_yeast_Intensity_Sample_Population.txt"
    # fn = r"/Users/dblyon/modules/cpr/agotool/static/data/exampledata/DEBUG.txt"
    # fn = r"/Users/dblyon/Downloads/Data for agotool 2017-01-30.txt"
    # fn = r"/Users/dblyon/Downloads/1A_Data_for_web_tool_test_AbundaceCorrection_fUbi.txt"
    # # import db_config
    # # ECHO = False
    # # TESTING = False
    # # DO_LOGGING = False
    # # connection = db_config.Connect(echo=ECHO, testing=TESTING, do_logging=DO_LOGGING)
    #
    # import io
    # fn = io.open(fn, mode='r')
    # ui = Userinput(fn=fn, foreground_string=None,
    #     background_string=None, col_foreground='foreground',
    #     col_background='background', col_intensity='intensity',
    #     num_bins=100, decimal='.', enrichment_method="abundance_correction")#, connection=connection)
    # # print(ui.iter_bins().next())

    ## testing UserInput
    # example1: foreground is proper subset of background, everything has an abundance value
    df_test = pd.DataFrame()
    df_test["background"] = pd.Series(['Q9UHI6', 'Q13075', 'A6NDB9', 'A6NFR9', 'O95359', 'D6RGG6', 'Q9BRQ0', 'P09629', 'Q9Y6G5', 'Q96KG9', 'Q8WXE0', 'Q6VB85', 'P13747', 'Q9UQ03', 'Q8N8S7'])
    df_test["intensity"] = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10] + [1] * 5, dtype=float)
    df_test["foreground"] = pd.Series(['Q9UHI6', 'Q13075', 'A6NDB9', 'A6NFR9', 'O95359', 'D6RGG6', 'Q9BRQ0', 'P09629', 'Q9Y6G5', 'Q96KG9'])
    df_test = df_test.sort_values(["intensity", "background"])

    in_ = "%0d".join([str(ele) for ele in df_test.loc[df_test.intensity.notnull(), "intensity"].tolist()])
    fg = "%0d".join(df_test.loc[df_test.foreground.notnull(), "foreground"].tolist())
    bg = "%0d".join(df_test.loc[df_test.background.notnull(), "background"].tolist())
    pqo = None
    # pqo = query.PersistentQueryObject()
    ui = REST_API_input(pqo=pqo, foreground_string=fg, background_string=bg, background_intensity=in_, num_bins=10)

    # every AN from foreground present, nothing is downweighed, since same abundance
    counter = 1
    for ans, weight_fac in ui.iter_bins():
        print(counter, ans, weight_fac)
        counter += 1

