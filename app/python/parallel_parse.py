import os, subprocess, sys, shutil
PLATFORM = sys.platform
NUMBER_OF_PROCESSES = 24


def concatenate_files(fn_list, fn_out):
    print("concatenating files to {}".format(fn_out))
    with open(fn_out, "w") as fh_out:
        for fn in fn_list:
            # print(fn)
            with open(fn, "r") as fh_in:
                for line in fh_in:
                    fh_out.write(line)

def sort_file(fn_in, fn_out, columns="1", fn_bash_script=None, number_of_processes=None, verbose=True):
    if number_of_processes is None:
        number_of_processes = NUMBER_OF_PROCESSES
    if number_of_processes > 10:
        number_of_processes = 10
    if verbose:
        print("#sorting file\nfn_in:\n{}\nfn_out:\n{}".format(fn_in, fn_out))
    if fn_bash_script is None:
        fn_bash_script = "bash_script_sort_{}.sh".format(os.path.basename(fn_in))
    with open(fn_bash_script, "w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        if PLATFORM == "linux":
            shellcmd = "sort --parallel {} -k {} {} -o {}".format(number_of_processes, columns, fn_in, fn_out)
        else:
            shellcmd = "LC_ALL=C gsort --parallel {} -k {} {} -o {}".format(number_of_processes, columns, fn_in, fn_out)
        fh.write(shellcmd)
    if verbose:
        print(shellcmd)
    subprocess.call("chmod 744 ./{}".format(fn_bash_script), shell=True)
    subprocess.call("./{}".format(fn_bash_script), shell=True)
    os.remove(fn_bash_script)

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.
    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).
    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

def parallel_script(fn_2_split, python_script, fn_out, temp_dir=None, cpu_number=None, recstart=None, recend=None, KB_MB_GB="M", split_size=1000):
    # option to unzip with pigz
    # also try pigz for multithreaded compression/decompression
    # time pigz -c -d -p 10 /home/dblyon/agotool/data/PostgreSQL/downloads/pmc_medline.tsv.gz > /dev/null
    # wasn't faster
    if cpu_number is None:
        cpu_number = NUMBER_OF_PROCESSES
    if split_size is None:
        split_size = 1000
    if recstart is None:
        recstart = "\n" # ^ID (UniProt dump)
    if recend is None:
        recend = "\n" # \/\/ (UniProt dump)

    if temp_dir is None:
        temp_dir = os.path.join(os.path.dirname(fn_2_split), "temp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    # check if dir is empty and prompt to empty if not
    if len(os.listdir(temp_dir)) > 0:
        answer = query_yes_no("The temp dir {} is not empty. It contains {} # of files. Type 'yes' to delete its content and continue.".format(temp_dir, len(os.listdir(temp_dir))))
        if not answer:
            print("You chose to interrupt the program. Please cleanup the directory and try again.")
            sys.exit()
        else:
            for fn in [os.path.join(temp_dir, fn) for fn in os.listdir(temp_dir)]:
                os.unlink(fn)
    # run the python script in parallel
    # shellcmd = 'parallel -a {0} --gnu -j{1} --bar --pipepart --block {2}{7} --recstart "{3}" --joblog split_log.txt "python {4} > {5}/part_{6}.txt"'.format(
    # fn_2_split, cpu_number, split_size, recstart, python_script, temp_dir, "{#}", KB_MB_GB)
    shellcmd = 'parallel -a {0} --gnu -j{1} --bar --pipepart --block {2}{7} --recstart "{3}" --recend "{8}" --joblog split_log.txt "python {4} > {5}/part_{6}.txt"'.format(fn_2_split, cpu_number, split_size, recstart, python_script, temp_dir, "{#}", KB_MB_GB, recend)
    fn_bash_script = "bash_script_parallel_{}.sh".format(os.path.basename(fn_2_split))
    with open(fn_bash_script, "w") as fh:
        fh.write("#!/usr/bin/env bash\n")
        fh.write(shellcmd)
        print(shellcmd)
    subprocess.call("chmod 744 ./{}".format(fn_bash_script), shell=True)
    subprocess.call("./{}".format(fn_bash_script), shell=True)
    os.remove(fn_bash_script)

    ### concatenate
    print("concatenating temp files")
    fn_list = [os.path.join(temp_dir, fn) for fn in os.listdir(temp_dir)]
    concatenate_files(fn_list, fn_out)
    ### sort in place
    print("sorting concatenated file {}".format(fn_out))
    sort_file(fn_out, fn_out, number_of_processes=cpu_number)
    ### remove temp files
    # print("removing temp files")
    # shutil.rmtree(temp_dir)

    # remove unzipped file

if __name__ == "__main__":
    ### python parallel_parse.py
    ### textmining pmc medline
    fn_2_split = r"/mnt/mnemo5/dblyon/agotool/data/PostgreSQL/downloads/pmc_medline.tsv"
    python_script = r"/home/dblyon/agotool/app/python/parallel_parse_textmining_pmc_medline.py"
    fn_out = r"/home/dblyon/agotool/data/PostgreSQL/tables/Functions_table_PMID.txt"
    temp_dir = r"/home/dblyon/agotool/data/PostgreSQL/tables/temp"
    parallel_script(fn_2_split, python_script, fn_out, temp_dir=temp_dir)

# e.g. of working cmd
# parallel -a /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/downloads/pmc_medline.tsv --gnu -j24 --bar --pipepart --block 1000M --recstart "
# " --joblog split_log.txt "python /home/dblyon/agotool/app/python/parallel_parse_textmining_pmc_medline.py > /home/dblyon/agotool/data/PostgreSQL/tables/temp/part_{#}.txt"

# not working yet
# parallel -a /home/dblyon/agotool/data/PostgreSQL/downloads/uniprot_sprot.dat.gz --gnu -j24 --bar --pipepart --block 1000M --recstart "^ID" --recend "/\/" --joblog split_log.txt "python /home/dblyon/agotool/app/python/parallel_parse_UniProt_dump.py > /home/dblyon/agotool/data/PostgreSQL/tables/temp/part_{#}.txt"

# pigz -c -d -p 4 /home/dblyon/agotool/data/PostgreSQL/downloads/uniprot_sprot.dat.gz | parallel --gnu -j24 --bar --pipepart --block 1000M --recstart "^ID" --recend "/\/" --joblog split_log.txt "python /home/dblyon/agotool/app/python/parallel_parse_UniProt_dump.py > /home/dblyon/agotool/data/PostgreSQL/tables/temp/part_{#}.txt"