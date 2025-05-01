.PHONY: install run clean check-python kill test set-key

# Default target
all: install set-key run

# Check if Python 3 is installed
check-python:
	@which python3 > /dev/null || (echo "Python 3 is not installed.\
	 							   Please install it first:"; \
		echo "Windows: Download from https://www.python.org/downloads/"; \
		echo "Mac: brew install python3"; \
		echo "Ubuntu/Debian: sudo apt-get install python3"; \
		echo "Fedora: sudo dnf install python3"; \
		exit 1)
	@python3 -m pip --version > /dev/null || (echo "pip is not installed.\
	 										  Installing pip..."; \
		python3 -m ensurepip --upgrade)

# Set the RIOT API key in the .env file
set-key:
	@read -p "Enter your Riot API key: " apikey; \
	echo "RIOT_API_KEY=$$apikey" > .env; \
	echo "API key has been set in .env file"

# Install dependencies
install:
	$(MAKE) check-python
	pip install -r requirements.txt

# Check if API key is set and run the application
run:
	@if [ ! -f .env ]; then \
		$(MAKE) set-key; \
	fi
	python3 app.py

# Run the test suite
test:
	python3 -m pytest test_suite/test_backend.py

# Clean up cache and temporary files
clean:
	rm -f stats_cache.json
	rm -f .env
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +

# Kill the server if it's stuck
kill:
	@pkill -f "python3 app.py" || echo "Server not running"
