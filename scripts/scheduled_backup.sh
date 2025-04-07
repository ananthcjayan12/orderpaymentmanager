#!/bin/bash
# Simple scheduled backup script for Coolify

# Exit immediately if a command exits with a non-zero status
set -e

# Source environment variables if they exist
if [ -f /app/.env ]; then
    source /app/.env
fi

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if BACKUP_DIR environment variable is set and directory is writable
if [ ! -z "${BACKUP_DIR}" ]; then
    # Try to create the backup directory if it doesn't exist
    mkdir -p ${BACKUP_DIR} 2>/dev/null || {
        echo "ERROR: Cannot create backup directory at ${BACKUP_DIR}. Check permissions or use a different location."
        echo "Coolify note: The /app directory is usually read-only. Use /data/backups or /tmp/backups instead."
        exit 1
    }
    
    # Check if the directory is writable
    if [ ! -w "${BACKUP_DIR}" ]; then
        echo "ERROR: Backup directory ${BACKUP_DIR} is not writable."
        exit 1
    fi
    
    echo "Using backup directory: ${BACKUP_DIR}"
else
    echo "No BACKUP_DIR specified, using default location."
fi

# Run the backup script with full option
${SCRIPT_DIR}/db_backup.sh full

# Log the backup status
if [ $? -eq 0 ]; then
    echo "$(date): Scheduled backup completed successfully"
else
    echo "$(date): Scheduled backup failed" >&2
    exit 1
fi

exit 0 