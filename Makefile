.PHONY: test test-verbose run build clean

test:
	python3 test_finance.py && python3 test_complet.py

test-verbose:
	python3 test_finance.py -v && python3 test_complet.py -v

test-finance:
	python3 test_finance.py

run:
	python3 main.py

build:
	pyinstaller avec_bukavu.spec --clean

clean:
	rm -rf build dist __pycache__ *.spec.bak
