.PHONY: test test-verbose run build clean

test:
	python3 test_finance.py && python3 test_complet.py && python3 test_permissions.py && python3 test_recus.py && python3 test_modeles.py && python3 test_administration.py && python3 test_scenario.py

test-verbose:
	python3 test_finance.py -v && python3 test_complet.py -v && python3 test_permissions.py -v && python3 test_recus.py -v && python3 test_modeles.py -v && python3 test_administration.py -v && python3 test_scenario.py -v

test-finance:
	python3 test_finance.py

test-permissions:
	python3 test_permissions.py

test-recus:
	python3 test_recus.py

test-modeles:
	python3 test_modeles.py

test-administration:
	python3 test_administration.py

run:
	python3 main.py

build:
	pyinstaller avec_bukavu.spec --clean

clean:
	rm -rf build dist __pycache__ *.spec.bak
