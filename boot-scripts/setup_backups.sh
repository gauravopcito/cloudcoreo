#!/bin/bash
######################################################################
##
## Variables in this file:
##   - BACKUP_BUCKET
##   - BACKUP_BUCKET_REGION
##   - ENV
##   - MONGO_NAME
##   - MONGO_BACKUP_CRON

set -eux

pip install filechunkio

if ! rpm -qa | grep -q cloudcoreo-directory-backup; then
    yum install -y cloudcoreo-directory-backup
fi

echo "==============IN SETUP BACKUPS SCRIPT====================="

MY_AZ="$(curl -sL 169.254.169.254/latest/meta-data/placement/availability-zone)"
MY_REGION="$(echo ${MY_AZ%?})"
backup_cron="${MONGO_BACKUP_CRON:-0 * * * *}"
backup_bucket_region="${BACKUP_BUCKET_REGION:-us-east-1}"
backup_dump_dir="/opt/backups"

private_ip_address="${PRIVATE_IP_ADDRESS}"
#instance_ids="${INSTANCE_IDS}"
NAMESERVERS=("${private_ip_address}")
 
# get length of an array
tLen="${#NAMESERVERS[@]}"
 
# use for loop read all nameservers
for (( i=0; i<${tLen}; i++ ));
do
  echo "================${NAMESERVERS[$i]}================="
done

## lets set up pre and post restore scripts
script_dir="/var/tmp/cloudcoreo-directory-backup-scripts"
mkdir -p "$script_dir"
cat <<EOF > "${script_dir}/pre-backup.sh"
#!/bin/bash
mongodump --out ${backup_dump_dir}
exit 0
EOF
cat <<EOF > "${script_dir}/post-backup.sh"
#!/bin/bash
rm -rf ${backup_dump_dir}/*
exit 0
EOF
cat <<EOF > "${script_dir}/pre-restore.sh"
#!/bin/bash
/etc/init.d/mongod stop
EOF
cat <<EOF > "${script_dir}/post-restore.sh"
#!/bin/bash
set -eux
mongorestore ${backup_dump_dir}
/etc/init.d/mongod start
EOF

S3_PREFIX="${MY_REGION}/mongo/${ENV}/${MONGO_NAME}"
## now we need to perform the restore
(
    cd /opt/; 
    python cloudcoreo-directory-backup.py --s3-backup-region ${backup_bucket_region} --s3-backup-bucket ${BACKUP_BUCKET} --s3-prefix "${S3_PREFIX}" --directory ${backup_dump_dir} --dump-dir /tmp --restore --post-restore-script "${script_dir}/post-restore.sh" --pre-restore-script "${script_dir}/pre-restore.sh"
)

## now that we are restored, lets set up the backups
echo "${backup_cron} ps -fwwC python | grep -q cloudcoreo-directory-backup || { cd /opt/; mkdir -p ${backup_dump_dir}; nohup python cloudcoreo-directory-backup.py --s3-backup-region ${backup_bucket_region} --s3-backup-bucket ${BACKUP_BUCKET} --s3-prefix $S3_PREFIX --directory ${backup_dump_dir} --dump-dir /tmp --pre-backup-script ${script_dir}pre-backup.sh --post-backup-script ${script_dir}/post-backup.sh & }" 
