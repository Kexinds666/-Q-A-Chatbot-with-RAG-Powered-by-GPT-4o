# RAG Chatbot Deployment Guide

This guide provides comprehensive instructions for deploying the RAG Chatbot system in various environments.

## Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Minimum 8GB RAM
- 20GB free disk space
- Ports 3000, 5000, 8000, 5432, 6379 available

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd rag-chatbot
make setup
```

### 2. Configure Environment

Edit the `.env` file with your configuration:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Customize other settings
OPENAI_MODEL=gpt-4o
FRONTEND_URL=http://localhost:3000
```

### 3. Deploy

```bash
# Start all services
make up

# Or use docker-compose directly
docker-compose up -d
```

### 4. Verify Deployment

```bash
# Check service health
make health

# Access the application
open http://localhost:3000
```

## Environment Configurations

### Development Environment

```bash
# Start development environment with hot reload
make dev
```

### Production Environment

```bash
# Deploy with production optimizations
make deploy-prod
```

### Staging Environment

```bash
# Use staging configuration
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

## Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Interface      │    │   AI Backend    │
│   (React)       │◄──►│  (Node.js)      │◄──►│   (FastAPI)     │
│   Port: 3000    │    │  Port: 5000     │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │     Redis       │    │   PostgreSQL    │
                       │   Port: 6379    │    │   Port: 5432    │
                       └─────────────────┘    └─────────────────┘
```

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | - | Yes |
| `OPENAI_MODEL` | GPT model to use | `gpt-4o` | No |
| `DATABASE_URL` | PostgreSQL connection string | Auto-generated | No |
| `REDIS_URL` | Redis connection string | `redis://redis:6379` | No |
| `FRONTEND_URL` | Frontend URL for CORS | `http://localhost:3000` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### Performance Tuning

#### Database Optimization

```sql
-- Increase connection pool
ALTER SYSTEM SET max_connections = 200;

-- Optimize memory settings
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '2GB';
```

#### Redis Configuration

```yaml
# In docker-compose.yml
redis:
  command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

#### Application Scaling

```yaml
# Scale services
docker-compose up -d --scale ai-backend=3 --scale interface-layer=2
```

## Monitoring and Logging

### Health Checks

```bash
# Check all services
make health

# Individual service checks
curl http://localhost:3000  # Frontend
curl http://localhost:5000/health  # Interface
curl http://localhost:8000/api/health  # AI Backend
```

### Logs

```bash
# View all logs
make logs

# View specific service logs
docker-compose logs -f ai-backend
docker-compose logs -f interface-layer
docker-compose logs -f frontend
```

### Metrics

The system provides metrics endpoints:

- Interface Layer: `http://localhost:5000/metrics`
- AI Backend: `http://localhost:8000/metrics`

## Load Testing

### Run Load Tests

```bash
# Basic load test
make load-test

# WebSocket load test
make load-test-ws

# Custom load test
cd tests && k6 run load-test.js --vus 500 --duration 10m
```

### Performance Targets

- **Throughput**: 500+ requests/second
- **Response Time**: 95th percentile < 2 seconds
- **Error Rate**: < 1%
- **Availability**: 99.9%

## Quality Evaluation

### Run RAGAS Evaluation

```bash
# Run evaluation
make evaluate

# View results
cat evaluation_results/rag_evaluation_results_*.json
```

### Evaluation Metrics

- **Faithfulness**: Factual consistency of answers
- **Answer Relevancy**: Relevance of answers to questions
- **Context Precision**: Precision of retrieved context
- **Context Recall**: Recall of retrieved context
- **Context Relevancy**: Relevancy of retrieved context

## Backup and Recovery

### Backup

```bash
# Create backup
make backup

# Manual backup
docker-compose exec postgres pg_dump -U rag_user rag_chatbot > backup.sql
```

### Recovery

```bash
# Restore from backup
make restore BACKUP=backup_file.sql

# Manual restore
docker-compose exec -T postgres psql -U rag_user rag_chatbot < backup.sql
```

## Security Considerations

### Production Security

1. **Use HTTPS**: Configure SSL certificates
2. **Environment Variables**: Never commit secrets
3. **Network Security**: Use private networks
4. **Access Control**: Implement authentication
5. **Rate Limiting**: Configure appropriate limits

### SSL Configuration

```yaml
# Add to docker-compose.yml
nginx:
  volumes:
    - ./ssl/cert.pem:/etc/nginx/ssl/cert.pem
    - ./ssl/key.pem:/etc/nginx/ssl/key.pem
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs service-name

# Check resources
docker stats

# Restart service
docker-compose restart service-name
```

#### Database Connection Issues

```bash
# Check database status
docker-compose exec postgres pg_isready -U rag_user

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### Memory Issues

```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.yml
services:
  ai-backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Performance Issues

1. **Slow Responses**: Check database and Redis performance
2. **High Memory Usage**: Optimize chunk sizes and batch processing
3. **Connection Timeouts**: Increase timeout settings
4. **Rate Limiting**: Adjust rate limits based on usage

## Scaling

### Horizontal Scaling

```yaml
# Scale services
docker-compose up -d --scale ai-backend=3 --scale interface-layer=2
```

### Vertical Scaling

```yaml
# Increase resources
services:
  ai-backend:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

### Load Balancing

```yaml
# Add load balancer
nginx:
  depends_on:
    - ai-backend
    - interface-layer
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf
```

## Maintenance

### Regular Tasks

1. **Database Maintenance**: Weekly vacuum and analyze
2. **Log Rotation**: Configure log rotation
3. **Backup Verification**: Test backup restoration
4. **Security Updates**: Keep dependencies updated
5. **Performance Monitoring**: Monitor metrics and logs

### Updates

```bash
# Update application
git pull
docker-compose build
docker-compose up -d

# Update dependencies
make install
```

## Support

For issues and questions:

1. Check the logs: `make logs`
2. Run health checks: `make health`
3. Review this documentation
4. Check GitHub issues
5. Contact support team

## License

This project is licensed under the MIT License.
