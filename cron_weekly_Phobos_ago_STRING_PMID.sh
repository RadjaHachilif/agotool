#!/bin/bash
check_exit_status () {
  if [ ! $? = 0 ]; then exit; fi
}
TAR_CURRENT=aGOtool_PMID_pickle_current.tar.gz
TAR_BAK=bak_aGOtool_PMID_pickle_$(date +"%Y_%m_%d_%I_%M_%p").tar.gz
global_enrichment_data_current=global_enrichment_data_current.tar.gz
populate_classification_schema_current=populate_classification_schema_current.sql.gz
TAR_GED_ALL_CURRENT=GED_all_current.tar
TAR_GED_ALL_BAK=bak_GED_all_$(date +"%Y_%m_%d_%I_%M_%p").tar
<<<<<<< HEAD
GED_DIR=/mnt/mnemo5/rhachilif/global_enrichment_v11
APP_DIR=/mnt/mnemo5/rhachilif/ago_STRING/agotool/app
PYTHON_DIR=/mnt/mnemo5/rhachilif/ago_STRING/agotool/app/python
TABLES_DIR=/mnt/mnemo5/rhachilif/ago_STRING/agotool/data/PostgreSQL/tables
SNAKEMAKE_EXE=/mnt/mnemo5/rhachilif/anaconda3/envs/agotool/bin/snakemake
PYTEST_EXE=/mnt/mnemo5/rhachilif/anaconda3/envs/agotool/bin/pytest
UWSGI_EXE=/mnt/mnemo5/rhachilif/anaconda3/envs/agotool/bin/uwsgi
TESTING_DIR=/mnt/mnemo5/rhachilif/ago_STRING/agotool/app/python/testing/sanity
=======
GED_DIR=/home/dblyon/global_enrichment_v11
APP_DIR=/home/dblyon/agotool_PMID_autoupdate/agotool/app
PYTHON_DIR=/home/dblyon/agotool_PMID_autoupdate/agotool/app/python
TABLES_DIR=/home/dblyon/agotool_PMID_autoupdate/agotool/data/PostgreSQL/tables
TABLES_DIR_PISCES=/home/dblyon/PMID_autoupdate/agotool/data/PostgreSQL/tables
SNAKEMAKE_EXE=/mnt/mnemo4/dblyon/install/anaconda3/envs/cron/bin/snakemake
PYTEST_EXE=/mnt/mnemo4/dblyon/install/anaconda3/envs/cron/bin/pytest
UWSGI_EXE=/mnt/mnemo4/dblyon/install/anaconda3/envs/cron/bin/uwsgi
TESTING_DIR=/home/dblyon/agotool_PMID_autoupdate/agotool/app/python/testing/sanity
>>>>>>> b4f3022146ab586b6aed74efb3031fd223469fe5

echo "--- Cronjob starting "$(date +"%Y_%m_%d_%I_%M_%p")" ---"
printf "\n ### run snakemake pipeline \n"
cd "$PYTHON_DIR" || exit
"$SNAKEMAKE_EXE" -l | tr '\n' ' ' | xargs "$SNAKEMAKE_EXE" -j 10 -F
check_exit_status

### test flat files
printf "\n PyTest flat files \n"
cd "$TESTING_DIR" || exit
"$PYTEST_EXE" test_flatfiles.py
check_exit_status

### start uWSGI and PyTest (agotool not running by default on Phobos)
printf "\n start uWSGI and PyTest \n"
cd "$APP_DIR" || exit
"$UWSGI_EXE" pytest_agotool_STRING.ini &
sleep 4m

## test API
printf "\n PyTest REST API \n"
cd "$TESTING_DIR" || exit
"$PYTEST_EXE" test_API_sanity.py --url testing
# -p no:cacheprovider
check_exit_status

## shutdown uWSGI flask app
cd "$APP_DIR" || exit
echo q > pytest.fifo
check_exit_status

#### tar and compress new files for transfer and backup
printf "\n ### tar and compress new files for transfer and backup \n"
cd "$TABLES_DIR" || exit
#### create tar.gz of relevant flat files
find . -maxdepth 1 -name "*_STS_FIN.p" -o -name "DF_file_dimensions_log.txt" -o -name "DF_global_enrichment_file_stats_log.txt" | xargs tar --overwrite -cvzf "$TAR_CURRENT"
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

<<<<<<< HEAD
#### copy files to production servers
#printf "\n### copy files to Aquarius (production server)\n"
#### San --> does pull instead of push via cronjob, data on Aquarius
#### Aquarius
#rsync -av "$TABLES_DIR"/"$TAR_CURRENT" dblyon@aquarius.meringlab.org:/home/dblyon/PMID_autoupdate/agotool/data/PostgreSQL/tables/"$TAR_CURRENT"
#check_exit_status
#rsync -av "$TABLES_DIR"/"$TAR_GED_ALL_CURRENT" dblyon@aquarius.meringlab.org:"$GED_DIR"/"$TAR_GED_ALL_CURRENT"
#check_exit_status

printf "\n### copy files to Pisces (production server)\n"
### Pisces
rsync -av "$TABLES_DIR"/"$TAR_CURRENT" rhachilif@pisces.meringlab.org:/mnt/mnemo5/rhachilif/ago_STRING/agotool/data/PostgreSQL/tables/"$TAR_FILE_NAME"
=======
#### Production server, decompress files and restart service
printf "\n### copy files to Pisces\n"
### copy files
rsync -av "$TABLES_DIR"/"$TAR_CURRENT" dblyon@pisces.meringlab.org:"$TABLES_DIR_PISCES"/"$TAR_CURRENT"
>>>>>>> b4f3022146ab586b6aed74efb3031fd223469fe5
check_exit_status
rsync -av "$TABLES_DIR"/"$TAR_GED_ALL_CURRENT" rhachilif@pisces.meringlab.org:"$GED_DIR"/"$TAR_GED_ALL_CURRENT"
check_exit_status
<<<<<<< HEAD

#### Production server, decompress files and restart service
#### Aquarius
#echo "run script on production server cron_weekly_Aquarius_ago_STRING_PMID.sh @ "$(date +"%Y_%m_%d_%I_%M_%p")" ---"
#ssh dblyon@aquarius.meringlab.org '/home/dblyon/PMID_autoupdate/agotool/cron_weekly_Aquarius_ago_STRING_PMID.sh &>> /home/dblyon/PMID_autoupdate/agotool/data/logs/log_updates.txt & disown'
#check_exit_status
### Pisces
echo "run script on Pisces production server cron_weekly_Pisces_ago_STRING_PMID.sh @ "$(date +"%Y_%m_%d_%I_%M_%p")" ---"
ssh rhachilif@pisces.meringlab.org '/mnt/mnemo5/rhachilif/ago_STRING/agotool/cron_weekly_Pisces_ago_STRING_PMID.sh &>> /mnt/mnemo5/rhachilif/ago_STRING/agotool/data/logs/log_updates.txt & disown'
=======
### run update
echo "run script on Pisces cron_weekly_Pisces_ago_STRING_PMID.sh @ "$(date +"%Y_%m_%d_%I_%M_%p")" ---"
ssh dblyon@pisces.meringlab.org '/home/dblyon/PMID_autoupdate/agotool/cron_weekly_Pisces_ago_STRING_PMID.sh &>> /home/dblyon/PMID_autoupdate/agotool/data/logs/log_updates.txt & disown'
>>>>>>> b4f3022146ab586b6aed74efb3031fd223469fe5
check_exit_status

printf "\n --- finished Cronjob --- \n"