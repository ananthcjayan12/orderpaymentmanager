# Define the Docker image name
IMAGE_NAME = order-payment-manager

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