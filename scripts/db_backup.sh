#!/bin/bash
# PostgreSQL Database Backup Script for Coolify

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration (can be overridden by environment variables)
: ${DB_NAME:=order_payment_db}
: ${DB_USER:=order_payment_user}
: ${DB_HOST:=db}
: ${DB_PORT:=5432}
# Password should be provided via PGPASSWORD environment variable or .pgpass file

# Backup directory setup - use /tmp/backups as default since /app may be read-only
BACKUP_DIR=${BACKUP_DIR:-/tmp/backups}
RETENTION_DAYS=${RETENTION_DAYS:-30}

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Generate timestamp for backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILENAME="${DB_NAME}_${TIMESTAMP}.sql"
COMPRESSED_BACKUP_FILENAME="${BACKUP_FILENAME}.gz"

# Log function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Backup function
perform_backup() {
    log "Starting database backup for ${DB_NAME}..."
    
    # Perform the database dump and compress it
    if [ -z "${PGPASSWORD}" ]; then
        log "Warning: PGPASSWORD environment variable not set. Using .pgpass file or password-less connection."
    fi
    
    log "Creating backup: ${BACKUP_DIR}/${COMPRESSED_BACKUP_FILENAME}"
    pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} | gzip > "${BACKUP_DIR}/${COMPRESSED_BACKUP_FILENAME}"
    
    if [ $? -eq 0 ]; then
        log "Backup completed successfully: ${BACKUP_DIR}/${COMPRESSED_BACKUP_FILENAME}"
        log "Backup size: $(du -h "${BACKUP_DIR}/${COMPRESSED_BACKUP_FILENAME}" | cut -f1)"
    else
        log "Error: Backup failed!"
        exit 1
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    find ${BACKUP_DIR} -name "${DB_NAME}_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -exec rm {} \;
    log "Cleanup completed."
}

# List all backups
list_backups() {
    log "Available backups for ${DB_NAME}:"
    ls -lh ${BACKUP_DIR}/${DB_NAME}_*.sql.gz 2>/dev/null || echo "No backups found."
}

# Restore from backup
restore_backup() {
    if [ -z "$1" ]; then
        log "Error: No backup file specified for restore."
        log "Usage: $0 restore /path/to/backup.sql.gz"
        exit 1
    fi
    
    BACKUP_FILE=$1
    
    if [ ! -f "${BACKUP_FILE}" ]; then
        log "Error: Backup file ${BACKUP_FILE} not found."
        exit 1
    fi
    
    log "Restoring database ${DB_NAME} from ${BACKUP_FILE}..."
    
    # If it's a compressed file, uncompress it first
    if [[ "${BACKUP_FILE}" == *.gz ]]; then
        log "Uncompressing backup file..."
        gunzip -c "${BACKUP_FILE}" | psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}
    else
        psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} < "${BACKUP_FILE}"
    fi
    
    if [ $? -eq 0 ]; then
        log "Database restored successfully."
    else
        log "Error: Database restore failed!"
        exit 1
    fi
}

# Main script execution
case "$1" in
    backup)
        perform_backup
        ;;
    cleanup)
        cleanup_old_backups
        ;;
    list)
        list_backups
        ;;
    restore)
        restore_backup "$2"
        ;;
    full)
        perform_backup
        cleanup_old_backups
        list_backups
        ;;
    *)
        echo "Usage: $0 {backup|cleanup|list|restore|full}"
        echo "  backup  - Create a new backup"
        echo "  cleanup - Remove backups older than ${RETENTION_DAYS} days"
        echo "  list    - List all available backups"
        echo "  restore - Restore from a backup file: $0 restore /path/to/backup.sql.gz"
        echo "  full    - Perform backup, cleanup old backups, and list available backups"
        exit 1
        ;;
esac

exit 0 