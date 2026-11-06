.PHONY: test check
test:
	python -m unittest discover -s tests -v
check: test
