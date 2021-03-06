import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.realpath(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))) # to get to python directory

import pytest
import requests
import ast

import variables, ratio, query, userinput, enrichment, run


def format_for_REST_API(list_of_string):
    return "%0d".join(list_of_string)

def test_count_terms_v3(random_foreground_background, pqo_STRING):
    """
    this test is for ratio.count_terms_v3,
    since it is testing for the presence of secondary IDs
    # goterm: 'GO:0007610' has secondary id 'GO:0044708'
    :param random_foreground_background:
    :param pqo_STRING:
    :return:
    """
    foreground, background, taxid = random_foreground_background
    etype_2_association_dict_foreground = pqo_STRING.get_association_dict_split_by_category(foreground)
    go_slim_or_basic = "basic"
    for entity_type in variables.entity_types_with_data_in_functions_table:
        obo_dag = run.pick_dag_from_entity_type_and_basic_or_slim(entity_type, go_slim_or_basic, pqo_STRING)
        assoc_dict = etype_2_association_dict_foreground[entity_type]
        for an in (AN for AN in set(foreground) if AN in assoc_dict):
            for association in assoc_dict[an]:
                association_id = obo_dag[association].id
                assert association_id == association

        association_2_count_dict_v2, association_2_ANs_dict_v2, ans_counter_v2 = ratio.count_terms_v2(set(background), assoc_dict, obo_dag)
        association_2_count_dict_v3, association_2_ANs_dict_v3, ans_counter_v3 = ratio.count_terms_v3(set(background), assoc_dict)
        assert association_2_count_dict_v2 == association_2_count_dict_v3
        assert association_2_ANs_dict_v2 == association_2_ANs_dict_v3
        assert ans_counter_v2 <= ans_counter_v3

def test_EnrichmentStudy_genome(random_foreground_background, pqo_STRING, args_dict):
    """
    checking for non empty results dictionary
    perc_association_foreground <= 100
    perc_asociation_background <= 100
    foreground_count <= foreground_n
    background_count <= background_n
    :return:
    """
    go_slim_or_basic = "basic"
    o_or_u_or_both = "overrepresented"
    multitest_method = "benjamini_hochberg"
    output_format = "json"
    foreground, background, taxid = random_foreground_background
    background_n = pqo_STRING.get_proteome_count_from_taxid(int(taxid))
    assert background_n == len(background)
    assert len(foreground) <= len(background)
    # ui = userinput.REST_API_input(pqo_STRING,
    #     foreground_string=format_for_REST_API(foreground),
    #     background_string=format_for_REST_API(background),
    #     enrichment_method="genome") #, background_n=len(background))

    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":format_for_REST_API(foreground),
                           "background":format_for_REST_API(background),
                           "enrichment_method":"genome"})
    ui = userinput.REST_API_input(pqo_STRING, args_dict_temp)

    etype_2_association_dict_foreground = pqo_STRING.get_association_dict_split_by_category(foreground)
    # assoc_dict = etype_2_association_dict_foreground[entity_type]

    etype_2_association_2_count_dict_background, etype_2_association_2_ANs_dict_background, _ = query.get_association_2_count_ANs_background_split_by_entity(taxid)
    for entity_type in variables.entity_types_with_data_in_functions_table:
        dag = run.pick_dag_from_entity_type_and_basic_or_slim(entity_type, go_slim_or_basic, pqo_STRING)
        assoc_dict = etype_2_association_dict_foreground[entity_type]
        if bool(assoc_dict): # not empty dictionary
            enrichment_study = enrichment.EnrichmentStudy(ui, assoc_dict, dag,
                o_or_u_or_both=o_or_u_or_both,
                multitest_method=multitest_method,
                entity_type=entity_type,
                association_2_count_dict_background=etype_2_association_2_count_dict_background[entity_type],
                background_n=background_n)
            result = enrichment_study.get_result(output_format)
            assert result # not an empty dict

@pytest.mark.STRING_examples
def test_run_STRING_enrichment(pqo_STRING, STRING_examples, args_dict):
    """
    checking that
    :param pqo_STRING: PersistentQuery Object
    :param STRING_examples: tuple (foreground ENSPs, taxid)
    :param args_dict: dict (from conftest.py with default values)
    :return
    :
    """
    enrichment_method = "compare_samples"
    foreground, taxid = STRING_examples
    background = query.get_proteins_of_taxid(taxid)
    # background_n = pqo_STRING.get_proteome_count_from_taxid(taxid)
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":format_for_REST_API(foreground),
                           "background":format_for_REST_API(background),
                           "intensity":None,
                           "enrichment_method":enrichment_method})
    # ui = userinput.REST_API_input(pqo_STRING, foreground_string=format_for_REST_API(foreground),
    #     background_string=format_for_REST_API(background), background_intensity=None, enrichment_method=enrichment_method)
    ui = userinput.REST_API_input(pqo_STRING, args_dict_temp)
    # results_all_function_types = run.run_STRING_enrichment(pqo=pqo_STRING, ui=ui, enrichment_method=enrichment_method,
    #     limit_2_entity_type=variables.limit_2_entity_types_ALL, output_format="json", FDR_cutoff=None)
    args_dict_temp.update({"limit_2_entity_type":variables.limit_2_entity_types_ALL,
                           "output_format":"json",
                           "FDR_cutoff":None})
    results_all_function_types = run.run_STRING_enrichment(pqo=pqo_STRING, ui=ui, args_dict=args_dict_temp)
    assert results_all_function_types  != {'message': 'Internal Server Error'}
    etypes = variables.entity_types_with_data_in_functions_table
    assert len(set(results_all_function_types.keys()).intersection(etypes)) == len(etypes)
    for _, result in results_all_function_types.items():
        # assert result is not empty
        assert result

@pytest.mark.STRING_examples
def test_run_STRING_enrichment_genome(pqo_STRING, STRING_examples, args_dict):
    foreground, taxid = STRING_examples
    etype_2_association_dict = pqo_STRING.get_association_dict_split_by_category(foreground)
    background_n = pqo_STRING.get_proteome_count_from_taxid(taxid)
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":format_for_REST_API(foreground),
                           "enrichment_method":"genome",
                           "background_n":background_n})
    # ui = userinput.REST_API_input(pqo_STRING, foreground_string=format_for_REST_API(foreground), enrichment_method="genome", background_n=background_n)
    ui = userinput.REST_API_input(pqo_STRING, args_dict_temp)
    # results_all_function_types = run.run_STRING_enrichment_genome(pqo=pqo_STRING, ui=ui, taxid=taxid, background_n=background_n, output_format="json", FDR_cutoff=None)
    args_dict_temp.update({"taxid":taxid,
                           "output_format":"json",
                           "FDR_cutoff":None})
    results_all_function_types = run.run_STRING_enrichment_genome(pqo=pqo_STRING, ui=ui, background_n=background_n, args_dict=args_dict_temp)
    assert results_all_function_types  != {'message': 'Internal Server Error'}
    # etypes = variables.entity_types_with_data_in_functions_table
    # assert len(set(results_all_function_types.keys()).intersection(etypes)) == len(etypes) # incomplete overlap can be due to missing functional annotations for given ENSPs
    for etype, result in results_all_function_types.items():
        result = ast.literal_eval(result)
        number_of_ENSPs_with_association = len(etype_2_association_dict[etype])
        # number_of_associations = len(set(val for key, val in etype_2_association_dict[etype].items()))
        number_of_associations = len({item for sublist in etype_2_association_dict[etype].values() for item in sublist})
        assert len(result) == number_of_associations # number of rows in results --> number of associations
        assert len(foreground) >= number_of_ENSPs_with_association # not every ENSP has functional associations

def test_EnrichmentStudy_(random_foreground_background, pqo_STRING, args_dict):
    """
    perc_association_foreground <= 100
    perc_asociation_background <= 100
    foreground_count <= foreground_n
    background_count <= background_n
    :return:
    """
    go_slim_or_basic = "basic"
    o_or_u_or_both = "overrepresented"
    multitest_method = "benjamini_hochberg"
    output_format = "json"
    foreground, background, taxid = random_foreground_background
    background_n = pqo_STRING.get_proteome_count_from_taxid(int(taxid))
    assert background_n == len(background)
    assert len(foreground) <= len(background)
    args_dict_temp = args_dict.copy()
    args_dict_temp.update({"foreground":format_for_REST_API(foreground),
                           "background":format_for_REST_API(background),
                           "enrichment_method":"genome",
                           "background_n":len(background)})
    # ui = userinput.REST_API_input(pqo_STRING,
    #     foreground_string=format_for_REST_API(foreground),
    #     background_string=format_for_REST_API(background),
    #     enrichment_method="genome", background_n=len(background))
    ui = userinput.REST_API_input(pqo_STRING, args_dict_temp)
    etype_2_association_dict_foreground = pqo_STRING.get_association_dict_split_by_category(foreground)
    etype_2_association_2_count_dict_background, etype_2_association_2_ANs_dict_background, _ = query.get_association_2_count_ANs_background_split_by_entity(taxid)
    for entity_type in variables.entity_types_with_data_in_functions_table:
        dag = run.pick_dag_from_entity_type_and_basic_or_slim(entity_type, go_slim_or_basic, pqo_STRING)
        assoc_dict = etype_2_association_dict_foreground[entity_type]
        if bool(assoc_dict): # not empty dictionary
            enrichment_study = enrichment.EnrichmentStudy(ui, assoc_dict, dag,
                o_or_u_or_both=o_or_u_or_both,
                multitest_method=multitest_method,
                entity_type=entity_type,
                association_2_count_dict_background=etype_2_association_2_count_dict_background[entity_type],
                background_n=background_n)
            result = enrichment_study.get_result(output_format)
            assert result # not an empty dict

# def test_example_files():
#     # assert 1 == 2
#     pass
#
@pytest.mark.STRING_examples
def test_REST_API_genome(STRING_examples):
    foreground, taxid = STRING_examples
    fg = "%0d".join(foreground)
    response = requests.post(variables.api_url, params={"output_format": "json",
                                                        "foreground": fg,
                                                        "enrichment_method": "genome",
                                                        "species": taxid})
    assert type(response.json()) == dict


# @pytest.mark.STRING_examples
# def test_REST_API_characterize_foreground(STRING_examples):
#     foreground, taxid = STRING_examples
#     fg = "%0d".join(foreground)
#     response = requests.post(variables.api_url, params={"output_format": "json",
#                                                         "foreground": fg,
#                                                         "enrichment_method": "characterize_foreground",
#                                                         "species": taxid})
#     assert type(response.json()) == dict
#
# @pytest.mark.STRING_examples
# def test_REST_API_compare_samples(STRING_examples):
#     foreground, taxid = STRING_examples
#     background = query.get_proteins_of_taxid(taxid)
#     fg = "%0d".join(foreground)
#     bg = "%0d".join(background)
#     response = requests.post(variables.api_url, params={"output_format": "json",
#                                                         "foreground": fg,
#                                                         "background": bg,
#                                                         "enrichment_method": "compare_samples",
#                                                         "species": taxid})
#     assert type(response.json()) == dict
#
# @pytest.mark.STRING_examples
# def test_REST_API_error(STRING_examples):
#     foreground, taxid = STRING_examples
#     background = query.get_proteins_of_taxid(taxid)
#     fg = "%0d".join(foreground)
#     bg = "%0d".join(background)
#     response = requests.post(variables.api_url, params={"output_format": "json",
#                                                         "foreground": fg,
#                                                         "background": bg,
#                                                         "enrichment_method": "compare_samples",
#                                                         "species": "INVALID_TAXID"})
#     assert type(response.json()) == dict
#
# @pytest.mark.xfail(reason="wrong URL test should fail")
# def test_wrong_URL(STRING_examples):
#     foreground, taxid = STRING_examples
#     background = query.get_proteins_of_taxid(taxid)
#     fg = "%0d".join(foreground)
#     bg = "%0d".join(background)
#     response = requests.post("www.bubu_was_here.com", params={"output_format": "json",
#                                                         "foreground": fg,
#                                                         "background": bg,
#                                                         "enrichment_method": "compare_samples",
#                                                         "species": "INVALID_TAXID"})
#     assert type(response.json()) == dict
