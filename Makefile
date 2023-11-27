all: clean prepare build start delay10s test


create-topics:
		docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic monitor \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_battery_control \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_ccu \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_communication_in \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_communication_out \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1 
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic data_aggregation \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic data_saver \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_diagnostic \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_engines \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1 
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_flight_controller \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_gps \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1 
	  docker exec broker \
  kafka-topics --create --if-not-exists \
    --topic drone_ins \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 1
	  


delay10s:
	sleep 10

sys-packages:
	# sudo apt install -y docker-compose
	sudo apt install python3-pip -y
	sudo pip3 install pipenv

pipenv:
	pipenv install -r requirements-dev.txt

prepare: clean sys-packages pipenv build

build:
	docker-compose build

rebuild:
	docker-compose build --force-rm

run:
	docker-compose up -d

start: run

restart:
	docker-compose restart

run-atm:
	pipenv run python atm/atm.py

run-fps:
	pipenv run python fps/fps.py

run-drone:
	pipenv run python drone/drone.py

logs:
	docker-compose logs -f --tail 100

test:
	pipenv run pytest -sv

stop:
	docker-compose stop

restart: stop start

clean:
	@pipenv --rm || echo no environment to remove
	@rm -rf Pipfile* || no pipfiles to remove
	@docker-compose down || echo no containers to remove	