PY ?= backend/.venv/bin/python

.PHONY: setup seed dev api ui eval

setup:
	python3 -m venv backend/.venv
	$(PY) -m pip install -r backend/requirements.txt
	cd frontend && npm install

seed:
	$(PY) -m data.generator.seed --seed 42

api:
	cd backend && ../$(PY) -m uvicorn app.main:app --host localhost --port 8010 --reload

ui:
	cd frontend && npm run dev

dev:
	$(MAKE) -j2 api ui

eval:
	$(PY) eval/evaluate.py
