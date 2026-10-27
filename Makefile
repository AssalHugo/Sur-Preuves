.PHONY: help setup check test lint fmt up down db-migrate backup review site poc

SHELL := /bin/bash
UV ?= uv
PYTHON ?= $(UV) run python
CSC ?= $(UV) run csc

help:
	@echo "Comparateur Science 2027 — Commandes disponibles :"
	@echo "  make setup       Installe les dépendances (backend uv, web npm) et initialise l'environnement"
	@echo "  make check       Vérification complète (lint, typage, tests backend + web)"
	@echo "  make test        Exécute les tests unitaires et d'intégration"
	@echo "  make lint        Vérifie le style (ruff, mypy, astro check)"
	@echo "  make fmt         Formate automatiquement le code Python (ruff)"
	@echo "  make up          Démarre le service PostgreSQL + pgvector local"
	@echo "  make down        Arrête les conteneurs Docker"
	@echo "  make db-migrate  Applique les migrations et initialise pgvector"
	@echo "  make backup      Réalise une sauvegarde pg_dump -Fc vers BACKUP_DIR"
	@echo "  make review      Démarre le back-office de relecture (127.0.0.1:8000)"
	@echo "  make site        Compile et sert le site statique Astro (127.0.0.1:4321)"
	@echo "  make poc         Enchaîne le pipeline POC complet (étapes reprenables)"

setup:
	@echo "==> Préparation de l'environnement..."
	@test -f .env || cp .env.example .env
	@mkdir -p var/pdf var/cache var/models var/backups
	@echo "==> Installation des dépendances Python (uv)..."
	@$(UV) venv
	@$(UV) pip install -e "backend[dev]"
	@echo "==> Installation des dépendances Web (npm)..."
	@cd web && npm install --no-audit --no-fund
	@echo "==> Configuration terminée avec succès."

check:
	@echo "==> [1/5] Vérification du formatage Python (ruff format)..."
	@$(UV) run ruff format --check .
	@echo "==> [2/5] Linting Python (ruff check)..."
	@$(UV) run ruff check .
	@echo "==> [3/5] Typage statique Python (mypy --strict)..."
	@$(UV) run mypy --strict backend/src backend/tests
	@echo "==> [4/5] Tests Python (pytest)..."
	@$(UV) run pytest
	@echo "==> [5/5] Vérification et build du site Astro..."
	@cd web && npm run check
	@cd web && npm run build
	@echo "==> Tous les contrôles sont au vert !"

test:
	@echo "==> Exécution des tests Python..."
	@$(UV) run pytest

lint:
	@echo "==> Linting Python et Web..."
	@$(UV) run ruff check .
	@$(UV) run mypy --strict backend/src backend/tests
	@cd web && npm run check

fmt:
	@echo "==> Formatage automatique..."
	@$(UV) run ruff format .
	@$(UV) run ruff check --fix .

up:
	@echo "==> Démarrage de PostgreSQL avec pgvector..."
	@docker compose up -d db
	@echo "==> Attente de la disponibilité de la base..."
	@until docker compose exec -T db pg_isready -U csc -d csc >/dev/null 2>&1; do \
		sleep 1; \
	done
	@echo "==> PostgreSQL est prêt sur 127.0.0.1 !"

down:
	@echo "==> Arrêt des services Docker..."
	@docker compose down

db-migrate:
	@echo "==> Initialisation de l'extension pgvector et migrations..."
	@$(CSC) db init

backup:
	@echo "==> Sauvegarde locale de la base de données..."
	@$(CSC) backup create

review:
	@echo "==> Démarrage du conteneur de relecture (profil review)..."
	@docker compose --profile review up -d review
	@echo "==> Back-office accessible sur http://127.0.0.1:8000"

site:
	@echo "==> Compilation et prévisualisation du site statique Astro..."
	@cd web && npm run build && npm run preview

poc:
	@echo "==> [POC 1/6] Ingestion documentaire..."
	@$(CSC) ingest
	@echo "==> [POC 2/6] Extraction des affirmations..."
	@$(CSC) extract
	@echo "==> [POC 3/6] Recherche de preuves scientifiques..."
	@$(CSC) evidence
	@echo "==> [POC 4/6] Synthèse des fiches..."
	@$(CSC) synth
	@echo "==> [POC 5/6] Vérification croisée..."
	@$(CSC) verify
	@echo "==> [POC 6/6] Publication du bundle POC..."
	@$(CSC) publish bundle --include-drafts --poc
	@echo "==> [POC 7/7] Lancement du site statique en local..."
	@$(MAKE) site
