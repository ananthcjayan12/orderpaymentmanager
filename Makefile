# Define the Docker image name
IMAGE_NAME = order-payment-manager

# Build the Docker image
build:
	docker-compose build

# Run the Docker container locally and map port 8000
run:
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