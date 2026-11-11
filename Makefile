.PHONY: test lint clean run

test:
	python3 -m unittest discover -s tests -v

lint:
	python3 -m compileall -q .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f analytics.db

run:
	python3 -m src.cli check
