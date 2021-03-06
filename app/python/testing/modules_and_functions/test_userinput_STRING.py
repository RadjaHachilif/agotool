import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.realpath(__file__))))
from io import StringIO
import werkzeug
import pandas as pd
import numpy as np
from itertools import zip_longest
import pytest

import userinput, variables

# TEST_FN_DIR = os.path.join(os.path.dirname(os.path.abspath(os.path.realpath(__file__))), "test")
PYTEST_FN_DIR = variables.PYTEST_FN_DIR

NUM_BINS = 100
DEFAULT_MISSING_BIN = -1


def from_file_2_df(fn):
    """
    :param fn: String
    :return: Tuple(Series, DataFrame)
    """
    df = pd.read_csv(fn, sep='\t')
    foreground = df["foreground"]
    if "intensity" in df.columns.tolist():
        background = df[["background", "intensity"]]
    else:
        background = df[["background"]]
    return foreground, background

### example1: foreground is a proper subset of the background, everything has an abundance value
# - example_1_STRING.txt: foreground is a proper subset of the background, everything has an abundance value, one row of NaNs
# - example_2_STRING.txt: same as example_1.txt with "," instead of "." as decimal delimiter
### example2: foreground is a proper subset of the background, not everything has an abundance value
# - example_11_STRING.txt: foreground is a proper subset of the background, not everything has an abundance value
### example3: foreground is not a proper subset of the background, not everything has an abundance value
# - example_3_STRING.txt: foreground is not a proper subset of the background, not everything has an abundance value
foreground_1, background_1 = from_file_2_df(os.path.join(variables.PYTEST_FN_DIR, "example_1_STRING.txt"))
foreground_2, background_2 = from_file_2_df(os.path.join(variables.PYTEST_FN_DIR, "example_2_STRING.txt"))
foreground_11, background_11 = from_file_2_df(os.path.join(variables.PYTEST_FN_DIR, "example_11_STRING.txt"))
foreground_3, background_3 = from_file_2_df(os.path.join(variables.PYTEST_FN_DIR, "example_3_STRING.txt"))
fg_bg_meth_expected_cases_DFs_with_IDs = [pytest.mark.parametrize(foreground_1, background_1, "abundance_correction"),
                                 (foreground_2, background_2, "abundance_correction"),
                                 (foreground_11, background_11, "abundance_correction"),
                                 (foreground_3, background_3, "abundance_correction")]
fg_bg_meth_expected_cases_ids = ["example_1_STRING.txt: foreground is a proper subset of the background, everything has an abundance value, one row of NaNs",
                                 'example_2_STRING.txt: same as example_1_STRING.txt with "," instead of "." as decimal delimiter',
                                 "example_11_STRING.txt: foreground is a proper subset of the background, not everything has an abundance value",
                                 "example_3_STRING.txt: foreground is not a proper subset of the background, not everything has an abundance value"]

### test cleanup for analysis for all 4 different enrichment methods
### via class REST_API_input
def test_cleanupforanalysis_abundance_correction_REST_API(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    """
    using fixture_fg_bg_meth_all
    python/test_userinput.py::test_cleanupforanalysis_abundance_correction_REST_API[edge case, empty DFs with NaNs] XPASS
    XPASS: should fail but passes.
    --> should not be tested at all, but doesn't matter
    """
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    enrichment_method = "abundance_correction"
    foreground_n = None
    background_n = None
    fg = format_for_REST_API(foreground)
    bg = format_for_REST_API(background["background"])
    in_ = format_for_REST_API(background["intensity"])
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground": fg, "background": bg, "intensity": in_, "num_bins": NUM_BINS,
        "enrichment_method": enrichment_method, "foreground_n": foreground_n, "background_n": background_n})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)
    assert ui.check_parse == True
    assert ui.check_cleanup == True

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0
    background = ui.background[ui.col_background]
    assert sum(background.isnull()) == 0
    assert sum(background.notnull()) > 0

    # every AN has an abundance val
    foreground_intensity = ui.foreground[ui.col_intensity]
    assert sum(foreground_intensity.isnull()) == 0
    assert sum(foreground_intensity.notnull()) > 0
    background_intensity = ui.background[ui.col_intensity]
    assert sum(background_intensity.isnull()) == 0
    assert sum(background_intensity.notnull()) > 0

    # foreground and background are strings and abundance values are floats
    assert isinstance(foreground.iloc[0], str)
    assert isinstance(background.iloc[0], str)
    assert isinstance(foreground_intensity.iloc[0], float)
    assert isinstance(background_intensity.iloc[0], float)

    # no duplicates
    assert foreground.duplicated().any() == False
    assert background.duplicated().any() == False

    # sorted abundance values
    assert non_decreasing(foreground_intensity.tolist()) == True
    assert non_decreasing(background_intensity.tolist()) == True

def test_cleanupforanalysis_characterize_foreground_REST_API(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    """
    python/test_userinput.py::test_cleanupforanalysis_characterize_foreground_REST_API[edge case, empty DFs with NaNs] XPASS
    """
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    enrichment_method = "characterize_foreground"
    foreground_n = None
    background_n = None
    fg = format_for_REST_API(foreground)
    bg = None
    in_ = None
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":fg, "background":bg, "intensity":in_, "num_bins":NUM_BINS,
        "enrichment_method":enrichment_method, "foreground_n":foreground_n, "background_n":background_n})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0

    # foreground
    assert isinstance(foreground.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False

def test_cleanupforanalysis_compare_samples_REST_API(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    """
    python/test_userinput.py::test_cleanupforanalysis_compare_samples_REST_API[edge case, empty DFs with NaNs] XPASS
    """
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    enrichment_method = "compare_samples"
    foreground_n = None
    background_n = None
    fg = format_for_REST_API(foreground)
    bg = format_for_REST_API(background["background"])
    in_ = None
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":fg, "background":bg, "intensity":in_, "num_bins":NUM_BINS,
        "enrichment_method":enrichment_method, "foreground_n":foreground_n, "background_n":background_n})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0
    background = ui.background[ui.col_background]
    assert sum(background.isnull()) == 0
    assert sum(background.notnull()) > 0

    # foreground and background are strings
    assert isinstance(foreground.iloc[0], str)
    assert isinstance(background.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False
    assert background.duplicated().any() == False

def test_cleanupforanalysis_compare_groups_REST_API(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    enrichment_method = "compare_groups"
    foreground_n = None
    background_n = None
    fg = format_for_REST_API(foreground)
    bg = format_for_REST_API(background["background"])
    in_ = None
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":fg, "background":bg, "intensity":in_, "num_bins":NUM_BINS,
        "enrichment_method":enrichment_method, "foreground_n":foreground_n, "background_n":background_n})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0
    background = ui.background[ui.col_background]
    assert sum(background.isnull()) == 0
    assert sum(background.notnull()) > 0

    # foreground and background are strings
    assert isinstance(foreground.iloc[0], str)
    assert isinstance(background.iloc[0], str)

    # if there were duplicates in the original input they should still be preserved in the cleaned up DF
    # not equal because of splice variants
    # remove NaNs from df_orig
    foreground_df_orig = ui.df_orig[ui.col_foreground]
    background_df_orig = ui.df_orig[ui.col_background]
    assert foreground.duplicated().sum() >= foreground_df_orig[foreground_df_orig.notnull()].duplicated().sum()
    assert background.duplicated().sum() >= background_df_orig[background_df_orig.notnull()].duplicated().sum()

def test_cleanupforanalysis_genome_REST_API(pqo_STRING, STRING_examples, args_dict):
    """
    python/test_userinput.py::test_cleanupforanalysis_characterize_foreground_REST_API[edge case, empty DFs with NaNs] XPASS
    """
    ENSPs, taxid = STRING_examples
    enrichment_method = "genome"
    foreground_n = None
    background_n = None
    fg = format_for_REST_API(ENSPs)
    bg = None
    in_ = None
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":fg, "background":bg, "intensity":in_, "num_bins":NUM_BINS,
        "enrichment_method":enrichment_method, "foreground_n":foreground_n, "background_n":background_n, "taxid": taxid})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0

    # foreground
    assert isinstance(foreground.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False

    foreground_n = ui.get_foreground_n()
    background_n = ui.get_background_n()
    assert background_n >= foreground_n

def test_random_REST_API_Input_abundance_correction(pqo_STRING, args_dict, random_abundance_correction_foreground_background):
    foreground, background, intensity, taxid = random_abundance_correction_foreground_background
    enrichment_method = "abundance_correction"
    args_dict["enrichment_method"] = enrichment_method
    args_dict["taxid"] = taxid
    args_dict["FDR_cutoff"] = 1
    args_dict["p_value_cutoff"] = 1
    args_dict["foreground"] = "%0d".join(foreground)
    args_dict["background"] = "%0d".join(background)
    args_dict["background_intensity"] = "%0d".join(intensity)
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict)
    assert ui.check_parse == True
    assert ui.check_cleanup == True
    num_rows, num_cols = ui.df_orig.shape
    assert num_cols == 3
    assert num_rows >= 200


### via class Userinput
def test_cleanupforanalysis_abundance_correction_Userinput(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    foreground, background, enrichment_method = fixture_fg_bg_meth_expected_cases
    if enrichment_method != "abundance_correction":
        # assert 1 == 1
        return None

    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = background.loc[background.background.notnull(), "background"].tolist()
    in_ = [str(ele) for ele in background.loc[background.intensity.notnull(), "intensity"].tolist()]
    background_string = ""
    for ele in zip(bg, in_):
        an, in_ = ele
        background_string += an + "\t" + in_ + "\n"
    args_dict_temp = args_dict.copy()
    args_dict_temp["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo_STRING, foreground_string=fg, background_string=background_string, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0
    background = ui.background[ui.col_background]
    assert sum(background.isnull()) == 0
    assert sum(background.notnull()) > 0

    # every AN has an abundance val
    foreground_intensity = ui.foreground[ui.col_intensity]
    assert sum(foreground_intensity.isnull()) == 0
    assert sum(foreground_intensity.notnull()) > 0
    background_intensity = ui.background[ui.col_intensity]
    assert sum(background_intensity.isnull()) == 0
    assert sum(background_intensity.notnull()) > 0

    # foreground and background are strings and abundance values are floats
    assert isinstance(foreground.iloc[0], str)
    assert isinstance(background.iloc[0], str)
    assert isinstance(foreground_intensity.iloc[0], float)
    assert isinstance(background_intensity.iloc[0], float)

    # no duplicates
    assert foreground.duplicated().any() == False
    assert background.duplicated().any() == False

    # sorted abundance values
    assert non_decreasing(foreground_intensity.tolist()) == True
    assert non_decreasing(background_intensity.tolist()) == True

def test_cleanupforanalysis_characterize_foreground_Userinput(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    enrichment_method = "characterize_foreground"
    args_dict_temp = args_dict.copy()
    args_dict_temp["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo_STRING, foreground_string=fg, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0

    # foreground
    assert isinstance(foreground.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False

def test_cleanupforanalysis_compare_samples_Userinput(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    enrichment_method = "compare_samples"
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = "\n".join(background.loc[background.background.notnull(), "background"].tolist())
    args_dict_temp = args_dict.copy()
    args_dict_temp["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo_STRING, foreground_string=fg, background_string=bg, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0
    background = ui.background[ui.col_background]
    assert sum(background.isnull()) == 0
    assert sum(background.notnull()) > 0

    # foreground and background are strings
    assert isinstance(foreground.iloc[0], str)
    assert isinstance(background.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False
    assert background.duplicated().any() == False

def test_cleanupforanalysis_compare_groups_Userinput(pqo_STRING, fixture_fg_bg_meth_expected_cases, args_dict):
    enrichment_method = "compare_groups"
    foreground, background, _ = fixture_fg_bg_meth_expected_cases
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = "\n".join(background.loc[background.background.notnull(), "background"].tolist())
    args_dict_temp = args_dict.copy()
    args_dict_temp["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo_STRING, foreground_string=fg, background_string=bg, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0
    background = ui.background[ui.col_background]
    assert sum(background.isnull()) == 0
    assert sum(background.notnull()) > 0

    # foreground and background are strings
    assert isinstance(foreground.iloc[0], str)
    assert isinstance(background.iloc[0], str)

    # if there were duplicates in the original input they should still be preserved in the cleaned up DF
    # not equal because of splice variants
    # remove NaNs from df_orig
    foreground_df_orig = ui.df_orig[ui.col_foreground]
    background_df_orig = ui.df_orig[ui.col_background]
    assert foreground.duplicated().sum() >= foreground_df_orig[foreground_df_orig.notnull()].duplicated().sum()
    assert background.duplicated().sum() >= background_df_orig[background_df_orig.notnull()].duplicated().sum()

def test_cleanupforanalysis_genome_Userinput_copyNpaste(pqo_STRING, STRING_examples, args_dict):
    """
    python/test_userinput.py::test_cleanupforanalysis_characterize_foreground_REST_API[edge case, empty DFs with NaNs] XPASS
    """
    ENSPs, taxid = STRING_examples
    fg = format_for_REST_API(ENSPs)
    enrichment_method = "genome"
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"enrichment_method":enrichment_method, "taxid": taxid})
    ui = userinput.Userinput(pqo_STRING, foreground_string=fg, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0

    # foreground
    assert isinstance(foreground.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False

    foreground_n = ui.get_foreground_n()
    background_n = ui.get_background_n()
    assert background_n >= foreground_n

def test_cleanupforanalysis_genome_Userinput_File(pqo_STRING, STRING_examples, args_dict):
    """
    python/test_userinput.py::test_cleanupforanalysis_characterize_foreground_REST_API[edge case, empty DFs with NaNs] XPASS
    """
    ENSPs, taxid = STRING_examples
    enrichment_method = "genome"
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"enrichment_method":enrichment_method, "taxid": taxid})
    werkzeug_fn = werkzeug.datastructures.FileStorage(stream=StringIO("foreground\n" + "\n".join(ENSPs)))
    werkzeug_fn.seek(0)
    ui = userinput.Userinput(pqo_STRING, fn=werkzeug_fn, args_dict=args_dict_temp)

    # no NaNs where ANs are expected
    foreground = ui.foreground[ui.col_foreground]
    assert sum(foreground.isnull()) == 0
    assert sum(foreground.notnull()) > 0

    # foreground
    assert isinstance(foreground.iloc[0], str)

    # no duplicates
    assert foreground.duplicated().any() == False

    foreground_n = ui.get_foreground_n()
    background_n = ui.get_background_n()
    assert background_n >= foreground_n


# example_1: foreground is a proper subset of the background, everything has an abundance value, one row of NaNs
# example_2: same as example_1 with "," instead of "." as decimal delimiter
### FileName_EnrichmentMethod
fn_em_0 = [pytest.param(os.path.join(PYTEST_FN_DIR, "example_1_STRING.txt"), "compare_samples"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_1_STRING.txt"), "compare_groups"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_1_STRING.txt"), "characterize_foreground"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_1.txt"), "unknown_method", marks=pytest.mark.xfail),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_2_STRING.txt"), "compare_samples"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_2_STRING.txt"), "compare_groups"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_2_STRING.txt"), "characterize_foreground"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_2_STRING.txt"), "unknown_method", marks=pytest.mark.xfail),
           pytest.param(os.path.join(PYTEST_FN_DIR, "file_does_not_exist.txt"), "compare_samples", marks=pytest.mark.xfail)]

# @pytest.mark.factory deprecated
@pytest.mark.parametrize("fn, enrichment_method", fn_em_0)
def test_factory_check_parse_and_cleanup(fn, enrichment_method, pqo_STRING, args_dict):
    args_dict["enrichment_method"] = enrichment_method
    ui_1 = get_ui_copy_and_paste(pqo=pqo_STRING, fn=fn, args_dict=args_dict)
    test_check_parse_cleanup_check(ui_1, check_parse=True, check_cleanup=True, check=True)
    assert ui_1.foreground.shape == (8, 1)
    if enrichment_method != "characterize_foreground":
        assert ui_1.background.shape == (11, 1)

    ui_2 = get_ui_fn(pqo=pqo_STRING, fn=fn, args_dict=args_dict)
    test_check_parse_cleanup_check(ui_2, check_parse=True, check_cleanup=True, check=True)
    assert ui_2.foreground.shape == (8, 1)
    if enrichment_method != "characterize_foreground":
        assert ui_2.background.shape == (11, 1)

    ui_3 = get_ui_fn(pqo=pqo_STRING, fn=fn, args_dict=args_dict)
    test_check_parse_cleanup_check(ui_3, check_parse=True, check_cleanup=True, check=True)
    assert ui_3.foreground.shape == (8, 1)
    if enrichment_method != "characterize_foreground":
        assert ui_3.background.shape == (11, 1)

    ### Check if the results are equal regardless if file, copy&paste, or REST-API
    assert ui_1.foreground.equals(ui_2.foreground)
    assert ui_2.foreground.equals(ui_3.foreground)
    if enrichment_method == "characterize_foreground":
        assert ui_1.background is None
        assert ui_2.background is None
        assert ui_3.background is None
    else:
        assert ui_1.background.equals(ui_2.background)
        assert ui_2.background.equals(ui_3.background)


# - example_1_STRING.txt: foreground is a proper subset of the background, everything has an abundance value, one row of NaNs
# - example_2_STRING.txt: same as example_1_STRING.txt with "," instead of "." as decimal delimiter
fn_em_1 = [pytest.param(os.path.join(PYTEST_FN_DIR, "example_1_STRING.txt"), "abundance_correction"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "example_2_STRING.txt"), "abundance_correction"),
           pytest.param(os.path.join(PYTEST_FN_DIR, "file_does_not_exist.txt"), "compare_samples", marks=pytest.mark.xfail)]

# @pytest.mark.factory
@pytest.mark.parametrize("fn, enrichment_method", fn_em_1)
def test_factory_check_parse_and_cleanup_abundance(fn, enrichment_method, pqo_STRING, args_dict):
    args_dict["enrichment_method"] = enrichment_method
    ui_1 = get_ui_copy_and_paste(pqo=pqo_STRING, fn=fn, args_dict=args_dict, with_abundance=True)
    test_check_parse_cleanup_check(ui_1, check_parse=True, check_cleanup=True, check=True)
    assert ui_1.foreground.shape == (8, 2)
    assert ui_1.background.shape == (11, 2)

    ui_2 = get_ui_fn(pqo=pqo_STRING, fn=fn, args_dict=args_dict)
    test_check_parse_cleanup_check(ui_2, check_parse=True, check_cleanup=True, check=True)
    assert ui_2.foreground.shape == (8, 2)
    assert ui_2.background.shape == (11, 2)

    ui_3 = get_ui_rest_api(args_dict, pqo=pqo_STRING, fn=fn, enrichment_method=enrichment_method, with_abundance=True)
    test_check_parse_cleanup_check(ui_3, check_parse=True, check_cleanup=True, check=True)
    assert ui_3.foreground.shape == (8, 2)
    assert ui_3.background.shape == (11, 2)

    ### Check if the results are equal regardless if file, copy&paste, or REST-API
    assert ui_1.foreground.equals(ui_2.foreground)
    assert ui_2.foreground.equals(ui_3.foreground)
    if enrichment_method == "characterize_foreground":
        assert ui_1.background is None
        assert ui_2.background is None
        assert ui_3.background is None
    else:
        assert ui_1.background.equals(ui_2.background)
        assert ui_2.background.equals(ui_3.background)


fg_bg_0 = [(foreground_1, background_1, "compare_samples"),
           (foreground_1, background_1, "compare_groups"),
           (foreground_1, background_1, "compare_samples")]

@pytest.mark.parametrize("foreground, background, enrichment_method", fg_bg_0)
def test_check_parse_with_copy_and_paste_0(foreground, background, enrichment_method, pqo_STRING, args_dict):
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = "\n".join(background.loc[background.background.notnull(), "background"].tolist())
    args_dict["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo=pqo_STRING, foreground_string=fg, background_string=bg, num_bins=NUM_BINS, args_dict=args_dict)
    assert ui.check_parse == True
    assert ui.foreground.shape == (8, 1)

fg_bg_1 = [(foreground_1, background_1, "abundance_correction")]

@pytest.mark.parametrize("foreground, background, enrichment_method", fg_bg_1)
def test_check_parse_with_copy_and_paste_1(foreground, background, enrichment_method, pqo_STRING, args_dict):
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = background.loc[background.background.notnull(), "background"].tolist()
    in_ = [str(ele) for ele in background.loc[background.intensity.notnull(), "intensity"].tolist()]
    background_string = ""
    for ele in zip_longest(bg, in_, fillvalue=np.nan):
        an, in_ = ele
        background_string += an + "\t" + str(in_) + "\n"
    args_dict["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo=pqo_STRING, foreground_string=fg, background_string=background_string, num_bins=NUM_BINS, args_dict=args_dict)
    assert ui.check_parse == True
    assert ui.foreground.shape == (8, 2)


### empty DF, edge case
foreground_empty = pd.Series(name="foreground", data={0: np.nan, 1: np.nan, 2: np.nan})
background_empty = pd.DataFrame({"background": {0: np.nan, 1: np.nan, 2: np.nan},
                                 "intensity": {0: np.nan, 1: np.nan, 2: np.nan}})
foreground_empty_1 = pd.Series(dtype="float64")
background_empty_1 = pd.DataFrame(dtype="float64")
foreground_empty_2 = [[], []]
background_empty_2 = [[], []]
foreground_empty_3 = []
background_empty_3 = []
foreground_empty_4 = None
background_empty_4 = None
foreground_almost_empty = pd.Series(name="foreground", data={0: np.nan, 1: "Q9UHI6", 2: np.nan})
### example0: nonesense AccessionNumbers, foreground is proper subset of background, everything has an abundance value
foreground_nonsense = pd.Series(name='foreground', data={0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J'})
background_nonsense = pd.DataFrame({'background': {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J', 10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O'},
                                    'intensity': {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 2.0, 7: 3.0, 8: 4.0, 9: 5.0, 10: 6.0, 11: 7.0, 12: 8.0, 13: 9.0, 14: 10.0}})

edge_cases_0 = [(foreground_empty, background_empty, "abundance_correction")]

fg_bg_meth_cp_abu = [pytest.param(foreground_empty, background_empty, "abundance_correction", marks=pytest.mark.xfail),
                     pytest.param(foreground_empty_2, background_empty_2, "abundance_correction", marks=pytest.mark.xfail),
                     pytest.param(foreground_empty_3, background_empty_3, "abundance_correction", marks=pytest.mark.xfail),
                     pytest.param(foreground_empty_4, background_empty_4, "abundance_correction", marks=pytest.mark.xfail),
                     pytest.param(foreground_nonsense, background_nonsense, "abundance_correction"),
                     pytest.param(foreground_1, background_1, "abundance_correction"),
                     pytest.param(foreground_2, background_2, "abundance_correction"),
                     pytest.param(foreground_3, background_3, "abundance_correction")]

fg_bg_iter_bins_DFs_with_IDs = [
    pytest.param(foreground_nonsense, background_nonsense, "abundance_correction", id="edge case: nonsense ANs"),
    pytest.param(foreground_1, background_1, "abundance_correction", id="example1: foreground is proper subset of background, everything has an abundance value"),
    pytest.param(foreground_2, background_2, "abundance_correction", id="example2: foreground is proper subset of background, not everything has an abundance value"),
    pytest.param(foreground_3, background_3, "abundance_correction", id="example3: foreground is not a proper subset of background, not everything has an abundance value"),
    pytest.param(foreground_empty, background_empty, "abundance_correction", marks=pytest.mark.xfail, id="edge case, empty DFs with NaNs"),
    pytest.param(foreground_empty_2, background_empty_2, "abundance_correction", marks=pytest.mark.xfail, id="edge case: nested empty list"),
    pytest.param(foreground_empty_3, background_empty_3, "abundance_correction", marks=pytest.mark.xfail, id="edge case: empty list"),
    pytest.param(foreground_empty_4, background_empty_4, "abundance_correction", marks=pytest.mark.xfail, id="edge case: None")]

@pytest.mark.parametrize("foreground, background, enrichment_method", edge_cases_0)
def test_check_parse_and_cleanup_copy_and_paste_0(foreground, background, enrichment_method, pqo_STRING, args_dict):
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = "\n".join(background.loc[background.background.notnull(), "background"].tolist())
    args_dict["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo=pqo_STRING, foreground_string=fg, background_string=bg, num_bins=NUM_BINS, args_dict=args_dict)
    assert ui.check_parse == False
    assert ui.check_cleanup == False
    assert ui.check == False

@pytest.mark.parametrize("foreground, background, enrichment_method", fg_bg_meth_cp_abu)
def test_check_parse_and_cleanup_copy_and_paste_1(foreground, background, enrichment_method, pqo_STRING, args_dict):
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = background.loc[background.background.notnull(), "background"].tolist()
    in_ = [str(ele) for ele in background.loc[background.intensity.notnull(), "intensity"].tolist()]
    background_string = ""
    for ele in zip_longest(bg, in_, fillvalue=np.nan):
        an, in_ = ele
        background_string += an + "\t" + str(in_) + "\n"
    args_dict["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo=pqo_STRING, foreground_string=fg, background_string=background_string, num_bins=NUM_BINS, args_dict=args_dict)
    assert ui.check_parse == True
    assert ui.check_cleanup == True
    assert ui.check == True

@pytest.mark.parametrize("foreground, background, enrichment_method", [(foreground_1, background_1, "compare_samples")])
def test_check_parse_and_cleanup_copy_and_paste_2(foreground, background, enrichment_method, pqo_STRING, args_dict):
    fg = "\n".join(foreground[foreground.notnull()].tolist())
    bg = "\n".join(background.loc[background.background.notnull(), "background"].tolist())
    args_dict["enrichment_method"] = enrichment_method
    ui = userinput.Userinput(pqo=pqo_STRING, foreground_string=fg, background_string=bg, num_bins=NUM_BINS, args_dict=args_dict)
    assert ui.check_parse == True

@pytest.mark.parametrize("foreground, background, enrichment_method", fg_bg_iter_bins_DFs_with_IDs)
def test_iter_bins_API_input(pqo_STRING, args_dict, foreground, background, enrichment_method):
    # foreground, background, enrichment_method = fg_bg_iter_bins_DFs
    fg = format_for_REST_API(foreground[foreground.notnull()])
    bg = format_for_REST_API(background.loc[background.background.notnull(), "background"])
    in_ = format_for_REST_API(background.loc[background.intensity.notnull(), "intensity"])
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":fg, "background":bg, "intensity":in_, "num_bins":NUM_BINS, "enrichment_method":enrichment_method})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)
    counter = 0
    for ans, weight_fac in ui.iter_bins():
        # every weighting factor is a float/int
        assert isinstance(weight_fac, float) or isinstance(weight_fac, int)
        counter += 1
    # will be 101 bins
    number_of_bins_used = pd.cut(ui.foreground["intensity"], bins=100, retbins=True)[1].shape[0]
    assert counter == number_of_bins_used

@pytest.mark.parametrize("foreground, background, enrichment_method", fg_bg_iter_bins_DFs_with_IDs)
def test_iter_bins_API_input_missing_bin(pqo_STRING, args_dict, foreground, background, enrichment_method):
    """
    this test only works if ANs fall within separate bins,
    e.g. for negative example:
       background  intensity foreground
    0           A        1.0          A
    1           B        1.0          B
    2           C        1.0          C
    """
    # foreground, background, enrichment_method = fixture_fg_bg_iter_bins
    fg = format_for_REST_API(foreground[foreground.notnull()])
    bg = format_for_REST_API(background.loc[background.background.notnull(), "background"])
    in_ = format_for_REST_API(background.loc[background.intensity.notnull(), "intensity"])

    # ui = userinput.REST_API_input(pqo=pqo_STRING, foreground_string=fg, background_string=bg, background_intensity=in_, num_bins=NUM_BINS, enrichment_method=enrichment_method)
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":fg, "background":bg, "intensity":in_, "num_bins":NUM_BINS, "enrichment_method":enrichment_method})
    ui = userinput.REST_API_input(pqo_STRING, args_dict=args_dict_temp)

    counter = 0
    for ans, weight_fac in ui.iter_bins():
        # every weighting factor is a float
        assert isinstance(weight_fac, float) or isinstance(weight_fac, int)
        counter += 1
    # since integers instead of floats are being used for test data, the number of unique bins can be determined by sets
    num_min_iterations_expected = len({int(ele) for ele in ui.foreground["intensity"].tolist()})
    assert counter >= num_min_iterations_expected


#############################################################################################
############################### helper functions
def non_decreasing(L):
    """
    https://stackoverflow.com/questions/4983258/python-how-to-check-list-monotonicity
    """
    return all(x<=y for x, y in zip(L, L[1:]))

def format_for_REST_API(pd_series):
    return "%0d".join([str(ele) for ele in list(pd_series)])

def get_ui_copy_and_paste(pqo, fn, args_dict, with_abundance=False, num_bins=NUM_BINS):
    df = pd.read_csv(fn, sep='\t')
    fg = "\n".join(df.loc[df["foreground"].notnull(), "foreground"].tolist())
    if not with_abundance:
        bg = "\n".join(df.loc[df["background"].notnull(), "background"].tolist())
        return userinput.Userinput(pqo=pqo, foreground_string=fg, background_string=bg, num_bins=num_bins, args_dict=args_dict)
    else:
        bg = df.loc[df["background"].notnull(), "background"].tolist()
        in_ = [str(ele) for ele in df.loc[df["intensity"].notnull(), "intensity"].tolist()]
        background_string = ""
        for ele in zip(bg, in_):
            an, in_ = ele
            background_string += an + "\t" + in_ + "\n"
        return userinput.Userinput(pqo=pqo, foreground_string=fg, background_string=background_string, num_bins=num_bins, args_dict=args_dict)

def get_ui_rest_api(args_dict, pqo, fn, enrichment_method, with_abundance=False, num_bins=NUM_BINS):
    df = pd.read_csv(fn, sep='\t')
    fg = format_for_REST_API(df.loc[df["foreground"].notnull(), "foreground"])
    bg = format_for_REST_API(df.loc[df["background"].notnull(), "background"])
    in_ = format_for_REST_API(df.loc[df["intensity"].notnull(), "intensity"])
    if with_abundance:
        args_dict_temp = args_dict.copy()
        args_dict_temp.update({"foreground": fg, "background": bg, "intensity": in_, "enrichment_method": enrichment_method, "num_bins": num_bins})
        return userinput.REST_API_input(pqo, args_dict=args_dict_temp)
        # return userinput.REST_API_input(pqo=pqo, foreground=fg, background_string=bg, background_intensity=in_, enrichment_method=enrichment_method)
    else:
        args_dict_temp = args_dict.copy()
        args_dict_temp.update({"foreground": fg, "background": bg, "enrichment_method": enrichment_method})
        # return userinput.REST_API_input(pqo=pqo, foreground=fg, background_string=bg, enrichment_method=enrichment_method, num_bins=num_bins)
        return userinput.REST_API_input(pqo, args_dict_temp)

def get_ui_fn(pqo, fn, args_dict, num_bins=NUM_BINS):
    return userinput.Userinput(pqo=pqo, fn=fn, args_dict=args_dict, num_bins=num_bins)

@pytest.mark.skip(reason="this test is being used internally, but will fail if run on its own since 'ui' is not a fixture but a parameter")
def test_check_parse_cleanup_check(ui, check_parse=True, check_cleanup=True, check=True):
    assert ui.check_parse == check_parse
    assert ui.check_cleanup == check_cleanup
    assert ui.check == check

def test_ui_rest_api_abundance_correction():
    pass
    # taxid = random.choice(query.get_taxids()) # read_from_flat_files=True
#         background = query.get_proteins_of_taxid(taxid)
#         foreground = random.sample(background, 200)
#         intensity = [str(ele) for ele in np.random.normal(size=len(background))]