# RAG Chatbot Makefile
# Provides convenient commands for development and deployment

.PHONY: help build up down logs clean test load-test evaluate dev

# Default target
help:
	@echo "RAG Chatbot - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  dev          - Start development environment"
	@echo "  build        - Build all Docker images"
	@echo "  up           - Start all services"
	@echo "  down         - Stop all services"
	@echo "  logs         - Show logs from all services"
	@echo "  clean        - Clean up containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  test         - Run all tests"
	@echo "  load-test    - Run k6 load tests"
	@echo "  evaluate     - Run RAGAS evaluation"
	@echo ""
	@echo "Utilities:"
	@echo "  setup        - Initial setup and configuration"
	@echo "  backup       - Backup database and data"
	@echo "  restore      - Restore from backup"

# Development environment
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Build all images
build:
	@echo "Building all Docker images..."
	docker-compose build --no-cache

# Start all services
up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started. Access the application at http://localhost:3000"

# Stop all services
down:
	@echo "Stopping all services..."
	docker-compose down

# Show logs
logs:
	docker-compose logs -f

# Clean up
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Run tests
test:
	@echo "Running tests..."
	cd tests && npm test

# Load testing
load-test:
	@echo "Running k6 load tests..."
	cd tests && k6 run load-test.js

# WebSocket load testing
load-test-ws:
	@echo "Running WebSocket load tests..."
	cd tests && k6 run websocket-test.js

# RAGAS evaluation
evaluate:
	@echo "Running RAGAS evaluation..."
	cd ai-backend && python scripts/evaluate_rag.py

# Initial setup
setup:
	@echo "Setting up RAG Chatbot..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp env.example .env; \
		echo "Please edit .env file with your configuration"; \
	fi
	@echo "Creating necessary directories..."
	mkdir -p data/chroma_db uploads processed logs evaluation_results
	@echo "Setup complete. Please configure your .env file and run 'make up'"

# Backup
backup:
	@echo "Creating backup..."
	mkdir -p backups
	docker-compose exec postgres pg_dump -U rag_user rag_chatbot > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql
	docker cp rag-chatbot-ai-backend:/app/data ./backups/data_backup_$(shell date +%Y%m%d_%H%M%S)

# Restore
restore:
	@echo "Available backups:"
	@ls -la backups/
	@echo "Please specify backup file: make restore BACKUP=backup_file.sql"

# Production deployment
deploy-prod:
	@echo "Deploying to production..."
	docker-compose --profile production up -d --build

# Health check
health:
	@echo "Checking service health..."
	@curl -f http://localhost:3000 > /dev/null && echo "Frontend: OK" || echo "Frontend: FAIL"
	@curl -f http://localhost:5000/health > /dev/null && echo "Interface: OK" || echo "Interface: FAIL"
	@curl -f http://localhost:8000/api/health > /dev/null && echo "AI Backend: OK" || echo "AI Backend: FAIL"

# Install dependencies
install:
	@echo "Installing dependencies..."
	cd frontend && npm install
	cd interface-layer && npm install
	cd ai-backend && pip install -r requirements.txt
	cd tests && npm install

# Format code
format:
	@echo "Formatting code..."
	cd frontend && npm run lint:fix
	cd interface-layer && npm run lint:fix
	cd ai-backend && black . && isort .

# Security scan
security:
	@echo "Running security scans..."
	cd frontend && npm audit
	cd interface-layer && npm audit
	cd ai-backend && safety check
