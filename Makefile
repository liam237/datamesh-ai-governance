PYTHON ?= python

.PHONY: install test all

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -q

# Une seule commande pour régénérer données, mécanismes, métriques et figures.
all:
	$(PYTHON) -m pipeline.run_all
