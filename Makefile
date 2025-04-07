# Define the Docker image name
IMAGE_NAME = order-payment-manager

# Development Commands
# -------------------

# Build the Docker image
build:
	docker-compose build

rebuild:
	docker-compose build --no-cache

# Run the Docker container locally and map port 8000
up:
	docker-compose up

# Run Django database migrations
migrate:
	docker-compose run --rm web python manage.py migrate

# Open a Django shell inside the container
shell:
	docker-compose run --rm web python manage.py shell

# Run Django tests
test:
	docker-compose run --rm web python manage.py test

# Access an interactive shell inside the Docker container
docker-shell:
	docker-compose run --rm web bash

# Production Commands
# ------------------

# Build the production Docker image
build-prod:
	docker-compose -f docker-compose.prod.yml build

# Build the production Docker image without using cache
rebuild-prod:
	docker-compose -f docker-compose.prod.yml build --no-cache

# Start production containers in detached mode
up-prod:
	docker-compose -f docker-compose.prod.yml up -d

# Stop production containers
down-prod:
	docker-compose -f docker-compose.prod.yml down

# View production logs
logs-prod:
	docker-compose -f docker-compose.prod.yml logs -f

# Run Django migrations in production
migrate-prod:
	docker-compose -f docker-compose.prod.yml run --rm web python manage.py migrate

# Collect static files in production
collectstatic-prod:
	docker-compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput

# Access a shell in the production web container
shell-prod:
	docker-compose -f docker-compose.prod.yml run --rm web bash

# Run Django management commands in production
django-command-prod:
	@echo "Usage: make django-command-prod CMD='your_command'"
	@docker-compose -f docker-compose.prod.yml run --rm web python manage.py $(CMD)

# Database Backup and Restore Commands
# -----------------------------------

# Create backup directory if it doesn't exist
BACKUP_DIR = ./backups
$(shell mkdir -p $(BACKUP_DIR))

# Get current date for backup filename
BACKUP_FILENAME = order_payment_db_$(shell date +%Y%m%d_%H%M%S).sql

# Backup the production database
backup-db:
	@echo "Creating database backup: $(BACKUP_DIR)/$(BACKUP_FILENAME)"
	docker-compose -f docker-compose.prod.yml exec db pg_dump -U order_payment_user -d order_payment_db > $(BACKUP_DIR)/$(BACKUP_FILENAME)
	@echo "Backup completed: $(BACKUP_DIR)/$(BACKUP_FILENAME)"

# List all available backups
list-backups:
	@echo "Available database backups:"
	@ls -lh $(BACKUP_DIR)

# Restore the database from a backup file
# Usage: make restore-db BACKUP_FILE=backups/your_backup_file.sql
restore-db:
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: BACKUP_FILE is required. Usage: make restore-db BACKUP_FILE=backups/your_backup_file.sql"; \
		exit 1; \
	fi
	@echo "Restoring database from $(BACKUP_FILE)..."
	docker-compose -f docker-compose.prod.yml exec -T db psql -U order_payment_user -d order_payment_db < $(BACKUP_FILE)
	@echo "Database restored successfully."

# Create a compressed backup of the production database
backup-db-gz:
	@echo "Creating compressed database backup..."
	docker-compose -f docker-compose.prod.yml exec db pg_dump -U order_payment_user -d order_payment_db | gzip > $(BACKUP_DIR)/$(BACKUP_FILENAME).gz
	@echo "Compressed backup completed: $(BACKUP_DIR)/$(BACKUP_FILENAME).gz"

# Scheduled backup (can be used with cron)
scheduled-backup:
	@echo "Running scheduled backup..."
	@$(MAKE) backup-db-gz
	@echo "Removing backups older than 30 days..."
	@find $(BACKUP_DIR) -name "order_payment_db_*.sql.gz" -type f -mtime +30 -delete

# Run the backup script inside the container
run-backup-script:
	@echo "Running backup script in production container..."
	docker-compose -f docker-compose.prod.yml exec web bash -c "/app/scripts/db_backup.sh full"

# Copy backups from container to local machine
fetch-latest-backup:
	@echo "Fetching latest backup from container..."
	@mkdir -p $(BACKUP_DIR)
	@container_id=$$(docker-compose -f docker-compose.prod.yml ps -q web); \
	latest_backup=$$(docker exec $$container_id find /data/backups -name "*.gz" -type f -printf "%T@ %p\n" | sort -nr | head -n1 | cut -d' ' -f2); \
	if [ -z "$$latest_backup" ]; then \
		echo "No backups found in container"; \
		exit 1; \
	fi; \
	filename=$$(basename $$latest_backup); \
	docker cp $$container_id:$$latest_backup $(BACKUP_DIR)/; \
	echo "Latest backup copied to $(BACKUP_DIR)/$$filename" 