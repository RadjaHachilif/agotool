#!/usr/bin/env python
import os, sys
import requests
import urllib.request, urllib.parse
from ftplib import FTP
from bs4 import BeautifulSoup
from retrying import retry

PYTHON_DIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
sys.path.insert(0, PYTHON_DIR)
import variables

DOWNLOADS_DIR = variables.DOWNLOADS_DIR_SNAKEMAKE
# DIRECTORIES_LIST = variables.DIRECTORIES_LIST
# SESSION_FOLDER_ABSOLUTE = variables.SESSION_FOLDER_ABSOLUTE


@retry(stop_max_attempt_number=5, wait_exponential_multiplier=50000)
def download_requests(url, file_name, verbose=True):
    """
    only works for http not ftp
    """
    file_name = os.path.join(DOWNLOADS_DIR, file_name)
    tmp_f = os.path.join(DOWNLOADS_DIR, file_name + ".tmp")
    url = url.replace(" ", "%20")
    if verbose:
        print("{}\nDownloading to: {}\n".format(url, file_name))
    r = requests.get(url, stream=True)
    with open(tmp_f, "wb") as fh:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                fh.write(chunk)
    os.rename(tmp_f, file_name)

@retry(stop_max_attempt_number=5, wait_exponential_multiplier=50000)
def download_gzip_file(url, file_name, verbose=True):
    """
    :param url: String
    :param file_name: String (absolute path of name of downloaded)
    :param verbose: Bool (flag to print infos)
    :return: None
    """
    CHUNK = 16 * 1024
    temp_fn = file_name + ".tmp"
    if verbose:
        print('\nDownloading: {}'.format(url))
        print('TO: {}'.format(file_name))
    try:
        with open(temp_fn, "wb") as temp_fh:
            response = urllib.request.urlopen(url)
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                temp_fh.write(chunk)
                temp_fh.flush()
    except IOError:
        print("Couldn't download {}".format(url))
        os.remove(temp_fn.name)
    os.rename(temp_fn, file_name)
    if verbose:
        print("finished download")

def download_GO_slim_subsets(url, download_dir, GO_slim_subsets_file):
    # url = r"http://purl.obolibrary.org/obo/go/subsets"
    # get URLs to download
    files_2_download = [fn for fn in sorted(set(get_list_of_files_2_download_from_http(url, ext="obo", go_subset=True))) if not os.path.basename(fn).startswith("gocheck")]
    with open(GO_slim_subsets_file, "w") as fh_out:
        for url in files_2_download:
            # check if needed, rename?
            basename = os.path.basename(url)
            file_name = os.path.join(download_dir, basename)
            download_requests(url, file_name, verbose=False)
            fh_out.write("{}\n".format(basename))

def download_WikiPathways(url, download_dir, Human_WikiPathways_gmt): #WikiPathways_not_a_gmt_file):
    """
    download flat files in GMT format
    Gene Matrix Transposed, lists of datanodes per pathway, unified to Entrez Gene identifiers.
    e.g.
    'http://data.wikipathways.org/current/gmt/wikipathways-20190310-gmt-Anopheles_gambiae.gmt'
    http://data.wikipathways.org/current/gmt
    """
    # get potential URLs to download
    files_2_download = sorted(set(get_list_of_files_2_download_from_http(url, ext="gmt")))
    # download and rename
    for url in files_2_download:
        # check if needed, rename?
        basename = os.path.basename(url)
        basename_split = basename.split("-")
        basename_without_date = "-".join([basename_split[0]] + basename_split[3:])
        file_name = os.path.join(download_dir, basename_without_date)
        download_requests(url, file_name, verbose=False)
    # with open(WikiPathways_not_a_gmt_file, "w") as fh_out:
    #     fh_out.write("downloaded {} number of gmt files".format(len(files_2_download)))
    assert os.path.exists(Human_WikiPathways_gmt)

def get_list_of_files_2_download_from_http(url, ext='', go_subset=False):
    page = requests.get(url).text
    soup = BeautifulSoup(page, 'html.parser')
    if go_subset:
        return [node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]
    else:
        return [url + '/' + node.get('href')[2:] for node in soup.find_all('a') if node.get('href').endswith(ext)]

def download_UniProt_reference_proteomes(download_dir, verbose=True):
    # UniProt_reference_proteomes_partial_link = r"ftp://ftp.expasy.org/databases/uniprot/current_release/knowledgebase/reference_proteomes"
    site = "ftp.expasy.org"
    files_2_download = []
    for domain in ["Eukaryota", "Bacteria", "Archaea", "Viruses"]:
        workdir = "databases/uniprot/current_release/knowledgebase/reference_proteomes/{}".format(domain)
        ftp = FTP(site)
        ftp.login()
        ftp.cwd(workdir)
        subdir_list = ftp.nlst()
        for subdir in subdir_list:  # e.g. UP000054539
            sub_workdir = "databases/uniprot/current_release/knowledgebase/reference_proteomes/{}/{}".format(domain, subdir)
            ftp = FTP(site)
            ftp.login()
            ftp.cwd(sub_workdir)
            for filename in ftp.nlst():
                if filename.startswith("UP"):# taxid, fasta, gz = "UP000002654_768679.fasta.gz".split("_")[-1].split(".")
                    taxid, fasta, gz = filename.split("_")[-1].split(".")
                    try:
                        _ = int(taxid)
                    except ValueError:
                        continue
                    if fasta == "fasta" and gz == "gz":
                        files_2_download.append("https://{}/{}/{}".format(site, sub_workdir, filename))
    files_2_download = sorted(set(files_2_download))
    if verbose:
        print("Found {} number of reference proteome fasta files to download".format(len(files_2_download)))
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    for url in files_2_download:
        file_name = os.path.join(download_dir, os.path.basename(url))
        download_gzip_file(url, file_name, verbose=False)



if __name__ == "__main__":
    DOWNLOADS_DIR = r"/Users/dblyon/modules/cpr/agotool/data/PostgreSQL/downloads"
    UniProt_reference_proteomes_dir = os.path.join(DOWNLOADS_DIR, "UniProt_ref_prots")
    download_UniProt_reference_proteomes(UniProt_reference_proteomes_dir, verbose=True)
