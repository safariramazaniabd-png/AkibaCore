.PHONY: test test-verbose run build clean

test:
	python3 test_finance.py

test-verbose:
	python3 test_finance.py -v

run:
	python3 main.py

build:
	pyinstaller avec_bukavu.spec --clean

clean:
	rm -rf build dist __pycache__ *.spec.bak
