# Database Backup Scripts for Coolify

This directory contains shell scripts for backing up and restoring your PostgreSQL database in a Coolify environment.

## Scripts Overview

1. `db_backup.sh` - Main backup and restore utility script
2. `scheduled_backup.sh` - Simple wrapper for scheduled backups

## How to Set Up in Coolify

### 1. Configure Environment Variables

In your Coolify deployment settings, add the following environment variables:

```
DB_NAME=order_payment_db
DB_USER=order_payment_user
DB_HOST=db
DB_PORT=5432
PGPASSWORD=your_database_password
BACKUP_DIR=/data/backups    # Important: Use a writable location
RETENTION_DAYS=30
```

> **Important Note**: The default backup location has been changed to `/tmp/backups` since `/app` is typically read-only in Coolify. However, `/tmp` is ephemeral and will be cleared when containers restart. For persistent storage, set `BACKUP_DIR` to a mounted volume path like `/data/backups`.

### 2. Set Up Scheduled Backups

Configure a Coolify scheduled job with the following command:

```
/app/scripts/scheduled_backup.sh
```

Set the frequency according to your needs (recommended: daily).

### 3. Mount a Persistent Volume

**Critical for Data Persistence**: You MUST configure a volume for your backups or they will be lost!

In Coolify, set up a volume mapping:

```
Host path: /your/persistent/storage/path
Container path: /data/backups
```

Then set the `BACKUP_DIR` environment variable to `/data/backups`.

## Manual Usage

If you need to run the backup scripts manually via SSH or the Coolify terminal:

```bash
# Create a backup
./scripts/db_backup.sh backup

# List existing backups
./scripts/db_backup.sh list

# Restore from a backup file
./scripts/db_backup.sh restore /data/backups/order_payment_db_20231025_143022.sql.gz

# Run full backup cycle (backup + cleanup old backups + list available backups)
./scripts/db_backup.sh full
```

## Troubleshooting

### Read-Only Filesystem Errors

If you see errors like `mkdir: /app: Read-only file system`:

1. Make sure you've set the `BACKUP_DIR` environment variable to a writable location
2. Verify your volume is properly mounted in Coolify
3. Try using `/tmp/backups` temporarily for testing (note: this is not persistent)

### Accessing Backups Outside the Container

To copy backups from your Coolify container to another location:

```bash
# From your host machine:
docker cp coolify_container_name:/data/backups/your_backup.sql.gz /local/path/
```

## Restoring in a New Deployment

If you need to restore your database in a new Coolify deployment:

1. Copy the backup file to the new environment
2. Update the environment variables if necessary
3. Run the restore command:
   ```bash
   ./scripts/db_backup.sh restore /path/to/backup.sql.gz
   ```

## Additional Notes

- The scripts are configured to compress backups to save disk space
- By default, backups older than 30 days are automatically removed
- All operations are logged with timestamps for easy troubleshooting
- The backup directory is created automatically if it doesn't exist 