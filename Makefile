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