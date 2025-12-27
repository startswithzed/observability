.PHONY: build build-no-cache makemigrations migrate up clean

build:
	docker-compose build

build-no-cache:
	docker-compose build --no-cache

makemigrations:
	docker-compose run api python src/manage.py makemigrations

migrate:
	docker-compose run api python src/manage.py migrate

up:
	docker-compose up

clean:
	docker-compose down -v --remove-orphans