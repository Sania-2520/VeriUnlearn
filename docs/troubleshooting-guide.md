# Troubleshooting Guide — VeriUnlearn

## Common Issues

### Backend won't start

```bash
# Check PostgreSQL is running
docker compose ps postgres
docker compose logs postgres

# Check database migration
cd packages/backend && alembic upgrade head

# Check port availability
netstat -ano | findstr :8000
```

### ML Engine not responding

```bash
# Check GPU availability
nvidia-smi
docker compose logs ml-engine

# Test direct health
curl http://localhost:8001/health
```

### Celery tasks fail

```bash
# Check Redis connectivity
docker compose logs redis
redis-cli -a veriunlearn_secret ping

# Check Celery worker status
celery -A app.workers.celery_app inspect ping

# View task results
celery -A app.workers.celery_app result <task_id>
```

### Frontend shows 502 Bad Gateway

- Backend is not running or unhealthy
- Check `curl http://localhost:8000/health`
- Restart backend: `make dev-backend`

### LoRA training fails

```bash
# Check disk space for checkpoints
df -h

# Check PEFT availability
python -c "from peft import LoraConfig; print('OK')"

# Increase timeout if training large models
```

### Adapter lifecycle state not persisting

- Check `persist_path` in `LifecycleConfig`
- Ensure write permissions to `./adapter_registry/`
- JSON file may be corrupted — delete and restart

### Docker build fails

```bash
# Clear Docker cache
docker compose build --no-cache

# Check Docker disk space
docker system df

# Prune unused resources
docker system prune -f
```

## Getting Help

- Open an issue on GitHub
- Check existing issues for solutions
- Provide logs, steps to reproduce, and environment details
