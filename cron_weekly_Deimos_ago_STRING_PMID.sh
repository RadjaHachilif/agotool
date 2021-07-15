#!/bin/bash
### called from Deimos
### /home/rhachilif/agotool/cron_weekly_rhachilif_ago_STRING_PMID.sh &>> /home/rhachilf/agotool/data/logs/log_updates.txt & disown
check_exit_status () {
  if [ ! $? = 0 ]; then exit; fi
}
TABLES_DIR=/home/rhachilif/agotool/data/PostgreSQL/tables
TABLES_DIR_Digamma=/home/rhachilif/agotool/data/PostgreSQL/tables
APP_DIR=/home/rhachilif/agotool/app
PYTHON_DIR=/home/rhachilif/agotool/app/python
SNAKEMAKE_EXE=/home/rhachilif/anaconda3/envs/agotool/bin/snakemake
PYTEST_EXE=/home/rhachilif/anaconda3/envs/agotool/bin/pytest
TESTING_DIR=/home/rhachilif/agotool/app/python/testing/sanity
TAR_GED_ALL_CURRENT=GED_all_current.tar
TAR_GED_ALL_BAK=bak_GED_all_$(date +"%Y_%m_%d_%I_%M_%p").tar
global_enrichment_data_current=global_enrichment_data_current.tar.gz
GED_DIR=/home/rhachilif/global_enrichment_v11
UWSGI_EXE=/home/rhachilif/anaconda3/envs/agotool/bin/uwsgi
populate_classification_schema_current=populate_classification_schema_current.sql.gz
TAR_CURRENT=aGOtool_PMID_pickle_current.tar.gz
TAR_BAK=bak_aGOtool_PMID_pickle_$(date +"%Y_%m_%d_%I_%M_%p").tar.gz


echo "--- running script cron_weekly_rhachilif_update_aGOtool_PMID.sh @ "$(date +"%Y_%m_%d_%I_%M_%p")" ---"

#printf "\n ### run snakemake pipeline \n"
#cd "$PYTHON_DIR" || exit
#"$SNAKEMAKE_EXE" -l | tr '\n' ' ' | xargs "$SNAKEMAKE_EXE" -j 50 -F  --rerun-incomplete
#check_exit_status


### decompress files
printf "\n ### unpacking tar.gz files \n"
cd "$TABLES_DIR" || exit
tar --overwrite -xvzf "$TABLES_DIR"/aGOtool_PMID_pickle_current.tar.gz
check_exit_status
cd "$GED_DIR" || exit
tar --overwrite -xvf "$TAR_GED_ALL_CURRENT"
check_exit_status
tar --overwrite -xzf "$global_enrichment_data_current"
check_exit_status

### test flat files
printf "\n PyTest flat files \n"
cd "$TESTING_DIR" || exit
"$PYTEST_EXE" test_flatfiles.py
check_exit_status

## start a uWSGI testing app (additional sanity check, since switching back to chain-reloading)
printf "\n restart uWSGI and PyTest \n"
cd "$APP_DIR" || exit
"$UWSGI_EXE" vassal_agotool_STRING_pytest.ini &
sleep 4m
### test API
printf "\n PyTest REST API \n"
cd "$TESTING_DIR" || exit
"$PYTEST_EXE" test_API_sanity.py --url testing
check_exit_status
## shutdown uWSGI flask app
cd "$APP_DIR" || exit
echo q > pytest.fifo
check_exit_status

## restart uWSGI production app
printf "\n restart uWSGI and PyTest \n"
cd "$APP_DIR" || exit
# zerg-mode
#"$UWSGI_EXE" vassal_agotool_STRING.ini
# chain-reloading
echo c > ago_STRING_vassal.fifo
sleep 4m

## test API
printf "\n PyTest REST API \n"
cd "$TESTING_DIR" || exit
"$PYTEST_EXE" test_API_sanity.py --url production
check_exit_status

#### tar and compress new files for transfer and backup
printf "\n ### tar and compress new files for transfer and backup \n"
cd "$TABLES_DIR" || exit
#### create tar.gz of relevant flat files
find . -maxdepth 1 -name "*_STS_FIN.txt" -o -name "DF_file_dimensions_log.txt" -o -name "DF_global_enrichment_file_stats_log.txt" | xargs tar --overwrite -cvzf "$TAR_CURRENT"
check_exit_status
rsync -av "$TAR_CURRENT" "$TAR_BAK"
check_exit_status
### AFC_KS file: tar and gzip current
cd "$TABLES_DIR" || exit
check_exit_status
tar -cvf "$TAR_GED_ALL_CURRENT" "$global_enrichment_data_current" "$populate_classification_schema_current" "DF_global_enrichment_file_stats_log.txt"
check_exit_status
rsync -av "$TAR_GED_ALL_CURRENT" "$TAR_GED_ALL_BAK"
check_exit_status

### push files to Digamma
#printf "\n rsync push files from rhachilif to Digamma \n"
#rsync -Pave "ssh -i ~/.ssh/id_rsa_digamma" "$TABLES_DIR"/aGOtool_PMID_pickle_current.tar.gz rhachilif@digamma.embl.de:"$TABLES_DIR_Digamma"/aGOtool_PMID_pickle_current.tar.gz
#rsync -Pave "ssh -i ~/.ssh/id_rsa_digamma" "$GED_DIR"/"$TAR_GED_ALL_CURRENT" rhachilif@digamma.embl.de:"$GED_DIR"/"$TAR_GED_ALL_CURRENT"

#echo "now attempting to run update script on Digamma cron_weekly_Digamma_update_aGOtool_PMID.sh @ "$(date +"%Y_%m_%d_%I_%M_%p")" ---"
#ssh rhachilif@digamma.embl.de '/home/rhachilif/agotool/cron_weekly_Digamma_ago_STRING_PMID.sh &> /home/rhachilif/agotool/data/logs/log_updates.txt & disown'
#check_exit_status

printf " --- done --- \n "

