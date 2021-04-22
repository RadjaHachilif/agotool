#!/bin/sh
##### Aquarius for agotool_PMID_autoupdate
#### vim /home/rhachilif/PMID_autoupdate/agotool/app/static/fixpermissions.sh
### this is aimed at fixing file permissions for Nginx on Aquarius
chmod -R 755 /home/rhachilif/PMID_autoupdate/agotool/app/static
chmod 777 /home/rhachilif/PMID_autoupdate/agotool/cron_weekly_Aquarius_update_aGOtool_PMID.sh

# ### cd /home/rhachilif/PMID_autoupdate/agotool/.git/hooks
# ### vim post-checkout and post-merge
# #!/bin/sh
# chmod a+x /home/rhachilif/PMID_autoupdate/agotool/app/static/fixpermissions.sh
# /home/rhachilif/PMID_autoupdate/agotool/app/static/fixpermissions.sh
