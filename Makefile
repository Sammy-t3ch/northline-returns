.PHONY: test api up

test:
	cd backend && PYTHONPATH=. python tests_policy.py && PYTHONPATH=. pytest -q

api:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

up:
	docker compose up --build
