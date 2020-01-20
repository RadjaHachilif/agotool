#!/bin/bash

# shellcheck disable=SC2038
# shellcheck disable=SC2164
# shellcheck disable=SC2028
# shellcheck disable=SC2181

check_exit_status () {
  if [ ! $? = 0 ]; then exit; fi
}

### tar and compress previous files for backup
echo "\n### tar and compress previous files for backup\n"
TAR_FILE_NAME=bak_aGOtool_flatfiles_$(date +"%Y_%m_%d_%I_%M_%p").tar
cd /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables
### create tar of relevant flat files

find . -maxdepth 1 -name '*.npy' -o -name '*_UPS_FIN.txt' | xargs tar cvf $TAR_FILE_NAME
check_exit_status
### compress for quick transfer and backup, this can run in the background since it's independent of snakemake
pbzip2 -p24 $TAR_FILE_NAME &
check_exit_status

### run snakemake pipeline
echo "\n### run snakemake pipeline\n"
cd /mnt/mnemo5/dblyon/agotool/app/python
/mnt/mnemo5/dblyon/install/anaconda3/envs/snake/bin/snakemake -l | tr '\n' ' ' | xargs /mnt/mnemo5/dblyon/install/anaconda3/envs/snake/bin/snakemake -j 24 -F
check_exit_status

# tar and compress new files for backup
echo "\n### tar and compress new files for backup\n"
TAR_FILE_NAME=aGOtool_flatfiles_$(date +"%Y_%m_%d_%I_%M_%p").tar
cd /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables
# create tar of relevant flat files
find . -maxdepth 1 -name '*.npy' -o -name '*_UPS_FIN.txt' | xargs tar cvf $TAR_FILE_NAME
check_exit_status

# compress for quick transfer and backup, keep tar
pbzip2 -k -p20 $TAR_FILE_NAME
check_exit_status

# copy files to Aquarius (production server)
echo "\n### copy files to Aquarius (production server)\n"
rsync -av /mnt/mnemo5/dblyon/agotool/data/PostgreSQL/tables/"$TAR_FILE_NAME" dblyon@aquarius.meringlab.org:/home/dblyon/agotool/data/PostgreSQL/tables/
check_exit_status

ssh dblyon@aquarius '/home/dblyon/agotool/monthly_update_Aquarius.sh $TAR_FILE_NAME &> /home/dblyon/agotool/data/logs/log_updates.txt'
echo "\n--- finished cron job ---\n"


########################################################################################################################
### on production server "monthly_update_Aquarius.sh"
# pbzip2 -p10 -dc $TAR_FILE_NAME | tar x
# check if files are similar size of larger than previously
# copy from file SQL
# alter tables SQL

# restart service (hard restart)
#cd /mnt/mnemo5/dblyon/agotool/app
#/mnt/mnemo5/dblyon/install/anaconda3/envs/agotool/bin/uwsgi --reload uwsgi_aGOtool_master_PID.txt
# --> dockerize
########################################################################################################################

########################################################################################################################
### cron commands
# crontab -e --> modify
# crontab -l --> list
# crontab -r --> remove

### contents of crontab for dblyon
#MAILTO="dblyon@gmail.com" --> only if output not redirected, use log file instead
### dblyon inserted cronjob for automated aGOtool updates
## testing 10:05 am
# 1 1 1 * * /mnt/mnemo5/dblyon/agotool/cronjob_monthly_Atlas.sh >> /mnt/mnemo5/dblyon/agotool/log_cron_monthly_snakemake.txt 2>&1
########################################################################################################################