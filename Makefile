.PHONY: install run clean kill test set-key

all: install set-key run

set-key:
	@read -p "Enter your Riot API key: " apikey; \
	echo "RIOT_API_KEY=$$apikey" > .env; \
	echo "API key has been set in .env file"

install:
	pip install -r requirements.txt

run:
	@if [ ! -f .env ]; then \
		$(MAKE) set-key; \
	fi
	python3 app.py

test:
	python3 -m pytest test_suite/test_backend.py

clean:
	rm -f stats_cache.json
	rm -f .env
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +

kill:
	@pkill -f "python3 app.py" || echo "Server not running"
