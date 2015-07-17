# standard library
import os
import sys
import StringIO
import logging

# third party
import flask
from flask import render_template, request, send_from_directory
import wtforms
from wtforms import fields
import pandas as pd
import numpy as np

# local application
sys.path.append('static/python')
import run
import obo_parser
import cluster_filter

app = flask.Flask(__name__)
webserver_data  = os.getcwd() + '/static/data'
EXAMPLE_FOLDER = webserver_data + '/exampledata'
app.config['EXAMPLE_FOLDER'] = EXAMPLE_FOLDER
ALLOWED_EXTENSIONS = set(['txt', 'tsv'])

# Additional path settings for flask
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, 'data')
SCRIPT_DIR = os.path.join(APP_ROOT, 'scripts')

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)

species2files_dict = {
    "9606": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_human',
           'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Human_uniprot-proteome%3AUP000005640.tab'},
    "4932": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_yeast',
           'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Yeast_uniprot-proteome%3AUP000002311.tab'},
    "3702": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_arabidopsis',
           'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Arabidopsis_uniprot-proteome%3AUP000006548.tab'},
    "7955": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_zebrafish',
           'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Zebrafish_uniprot-proteome%3AUP000000437.tab'},
    "7227": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_fly',
           'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Fly_uniprot-proteome%3AUP000000803.tab'},
    "9031": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_chicken',
           'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Chicken_uniprot-proteome%3AUP000000539.tab'},
    "10090": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_mouse',
       'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Mouse_uniprot-proteome%3AUP000000589.tab'},
    "10116": {'goa_ref_fn': webserver_data + r'/GOA/gene_association.goa_rat',
       'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Rat_uniprot-proteome%3AUP000002494.tab'},
    "8364": {'uniprot_keywords_fn': webserver_data + r'/UniProt_Keywords/Frog_uniprot-proteome%3AUP000008143.tab'}
    }

# pre-load go_dag and goslim_dag (obo files) for speed
obo2file_dict = {"slim": webserver_data + r'/OBO/goslim_generic.obo',
                 "basic": webserver_data + r'/OBO/go-basic.obo'}
go_dag = obo_parser.GODag(obo_file=obo2file_dict['basic'])
goslim_dag = obo_parser.GODag(obo_file=obo2file_dict['slim'])

# filter results based on ancestors and descendants
filter = cluster_filter.Filter(go_dag)
# results_filtered = filter(header, results, indent)

# MCL clustering
mcl = cluster_filter.MCL_no_input_file_pid()
# cluster_list = mcl.calc_MCL_get_clusters(header, results, inflation_factor=2.0)


organism_choices = [
    (u'4932',  u'Saccharomyces cerevisiae'), # Yeast
    (u'9606',  u'Homo sapiens'), # Human
    (u'3702',  u'Arabidopsis thaliana'), # Arabidopsis
    (u'7955',  u'Danio rerio'), # Zebrafish
    (u'7227',  u'Drosophila melanogaster'), # Fly
    (u'9031',  u'Gallus gallus'), # Chicken
    (u'10090', u'Mus musculus'), # Mouse
    (u'10116', u'Rattus norvegicus') # Rat
    ]

################################################################################
# index.html
################################################################################
@app.route('/')
def index():
    return render_template('index.html')

################################################################################
# about.html
################################################################################
@app.route('/about')
def about():
    return render_template('about.html')

################################################################################
# results_zero.html
################################################################################
@app.route('/results_zero')
def gotupk_results_zero():
    return render_template('results_zero.html')

################################################################################
# page_not_found.html
################################################################################
@app.errorhandler(404)
def page_not_found(e):
    return render_template('page_not_found.html'), 404

################################################################################
# example.html
################################################################################
@app.route('/example')
def example():
    return render_template('example.html')

@app.route('/example/<path:filename>', methods=['GET', 'POST'])
def download_example_data(filename):
    uploads = app.config['EXAMPLE_FOLDER']
    return send_from_directory(directory=uploads, filename=filename)

################################################################################
################################################################################
# check user input
def check_userinput(userinput_fh, abcorr):
    decimal = '.'
    df = pd.read_csv(userinput_fh, sep='\t', decimal=decimal)
    userinput_fh.seek(0)
    if abcorr:
        if len(set(['population_an','population_int','sample_an']).intersection(set(df.columns.tolist()))) == 3:
            try:
                np.histogram(df['population_int'], bins=10)
            except TypeError:
                try:
                    decimal = ','
                    df = pd.read_csv(userinput_fh, sep='\t', decimal=decimal)
                    userinput_fh.seek(0)
                    np.histogram(df['population_int'], bins=10)
                except TypeError:
                    return False, decimal
            return True, decimal
    else:
        if len(set(['population_an', 'sample_an']).intersection(set(df.columns.tolist()))) == 2:
            return True, decimal
    return False, decimal

# validation of user inputs
def validate_float_larger_zero_smaller_one(form, field):
    if not 0 < field.data < 1:
        raise wtforms.ValidationError(" number must be: 0 < number < 1")

def validate_float_between_zero_and_one(form, field):
    if not 0 <= field.data <= 1:
        raise wtforms.ValidationError(" number must be: 0 <= number <= 1")

def validate_integer(form, field):
    if not isinstance(field.data, int):
        raise wtforms.ValidationError(" number must be an integer")

def validate_number(form, field):
    if not isinstance(field.data, (int, float)):
        raise wtforms.ValidationError(" must be a number")

def validate_inputfile(form, field):
    filename = request.files['userinput_file'].filename
    for extension in ALLOWED_EXTENSIONS:
        if filename.endswith('.' + extension):
            return True
    raise wtforms.ValidationError(
        " file must have a '.txt' or '.tsv' extension")


def resultfile_to_results(result_file):
    result_file.seek(0)
    header = result_file.readline().rstrip().split('\t')
    results = [line.split('\t') + [''] for line in result_file]
    result_file.seek(0)
    return results, header


################################################################################
# enrichment.html
################################################################################
class Enrichment_Form(wtforms.Form):
    organism = fields.SelectField(u'Select Organism',
                                  choices = organism_choices)

    userinput_file = fields.FileField("Choose File",
                                      [validate_inputfile])

    gocat_upk = fields.SelectField("GO-terms / UniProt-keywords",
                                   choices = (("all_GO", "all 3 GO categories"),
                                              ("BP", "Biological Process"),
                                              ("CP", "Celluar Compartment"),
                                              ("MF", "Molecular Function"),
                                              ("UPK", "UniProt-keywords")))

    abcorr = fields.BooleanField("Abundance correction",
                                 default = "checked")

    go_slim_or_basic = fields.SelectField("GO basic or slim",
                                          choices = (("basic", "basic"),
                                                     ("slim", "slim")))

    indent = fields.BooleanField("prepend GO-term level by dots",
                                 default = "checked")

    multitest_method = fields.SelectField(
        "Method for correction of multiple testing",
        choices = (("benjamini_hochberg", "Benjamini Hochberg"),
                   ("sidak", "Sidak"), ("holm", "Holm"),
                   ("bonferroni", "Bonferroni")))

    alpha = fields.FloatField("Alpha", [validate_float_larger_zero_smaller_one],
                              default = 0.05,
                              description = u"for multiple testing correction")
                              #!!! ??? where do the descriptions show up, how to make them visible??

    o_or_e_or_both = fields.SelectField("over- or under-represented or both",
                                        choices = (("both", "both"),
                                                   ("o", "overrepresented"),
                                                   ("u", "underrepresented")))

    num_bins = fields.IntegerField("Number of bins",
                                   [validate_integer],
                                   default = 100)

    backtracking = fields.BooleanField("Backtracking parent GO-terms",
                                       default = "checked")

    fold_enrichment_study2pop = fields.FloatField(
        "fold enrichment study/population",
        [validate_number], default = 0)

    p_value_uncorrected =  fields.FloatField(
        "p-value uncorrected",
        [validate_float_between_zero_and_one],
        default = 0)

    p_value_mulitpletesting =  fields.FloatField(
        "FDR-cutoff / p-value multiple testing",
        [validate_float_between_zero_and_one],
        default = 0)

@app.route('/enrichment')
def enrichment():
    return render_template('enrichment.html', form=Enrichment_Form())

@app.route('/results', methods=["GET", "POST"])
def results():
    """
    #!!!
    cluster_list = mcl.calc_MCL_get_clusters(header, results, inflation_factor=2.0)
    cluster_list: nested ListOfString corresponding to indices of results
    results_filtered = filter(header, results, indent)
    results_filtered: reduced version of results
    """
    form = Enrichment_Form(request.form)
    if request.method == 'POST' and form.validate():
        user_input_file = request.files['userinput_file']
        userinput_fh = StringIO.StringIO(user_input_file.read())
        check, decimal = check_userinput(userinput_fh, form.abcorr.data)
        if check:
            header, results = run.run(
                userinput_fh, decimal, form.organism.data, form.gocat_upk.data,
                form.go_slim_or_basic.data, form.indent.data,
                form.multitest_method.data, form.alpha.data,
                form.o_or_e_or_both.data, form.abcorr.data, form.num_bins.data,
                form.backtracking.data, form.fold_enrichment_study2pop.data,
                form.p_value_uncorrected.data,
                form.p_value_mulitpletesting.data, species2files_dict, go_dag,
                goslim_dag)
        else:
            return render_template('info_check_input.html')

        if len(results) == 0:
            return render_template('results_zero.html')
        else:
            header = header.split("\t")
            results2display = []
            for res in results:
                results2display.append(res.split('\t'))
            tsv = (u'%s\n%s\n' % (u'\t'.join(header), u'\n'.join(results))).encode('base64')
            return render_template('results.html', header=header, results=results2display, errors=[], tsv=tsv)

    return render_template('enrichment.html', form=form)


if __name__ == '__main__':
    #app.run('red', 5911, processes=4, debug=False)
    app.run(processes=4, debug=False)
















