# Docker Containerization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Dockerize the Zettelkasten MCP server to enable shared access across multiple users and VS Code instances.

**Architecture:** Run the MCP server as a long-running Docker container with persistent volumes for notes and database. Clients connect via stdio through `docker exec` instead of running local Python processes. This enables centralized knowledge management with concurrent access from multiple workspaces.

**Tech Stack:** Docker, Docker Compose, Python 3.10+, FastMCP, SQLite, volume mounts

---

## Task 1: Create Dockerfile

**Files:**

- Create: `Dockerfile`
- Reference: `pyproject.toml`, `src/zettelkasten_mcp/`

**Step 1: Create production-ready Dockerfile**

Create `Dockerfile` in the zettelkasten-mcp root:

```dockerfile
# Multi-stage build for smaller final image
FROM python:3.10-slim as builder

# Install uv for faster dependency installation
RUN pip install --no-cache-dir uv

WORKDIR /build

# Copy dependency files
COPY pyproject.toml setup.py ./
COPY src/ ./src/

# Install dependencies to a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -e .

# Final stage
FROM python:3.10-slim

# Create non-root user for security
RUN useradd -m -u 1000 zettel && \
    mkdir -p /data/notes /data/db && \
    chown -R zettel:zettel /data

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=zettel:zettel src/ /app/src/
COPY --chown=zettel:zettel pyproject.toml setup.py /app/

WORKDIR /app

# Set up environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ZETTELKASTEN_NOTES_DIR=/data/notes \
    ZETTELKASTEN_DATABASE_PATH=/data/db/zettelkasten.db \
    ZETTELKASTEN_BASE_DIR=/data \
    ZETTELKASTEN_LOG_LEVEL=INFO

# Switch to non-root user
USER zettel

# Expose volume mount points
VOLUME ["/data/notes", "/data/db"]

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from pathlib import Path; import sys; sys.exit(0 if Path('/data/notes').exists() and Path('/data/db').exists() else 1)"

# Run the MCP server
CMD ["python", "-m", "zettelkasten_mcp.main"]
```

**Step 2: Test local Docker build**

```bash
cd /home/kaesmad/projects/external/zettelkasten-mcp
docker build -t zettelkasten-mcp:latest .
```

Expected: Build completes successfully without errors

**Step 3: Verify image size and layers**

```bash
docker images zettelkasten-mcp:latest
docker history zettelkasten-mcp:latest
```

Expected: Image size < 500MB, clear layer structure

---

## Task 2: Create .dockerignore

**Files:**

- Create: `.dockerignore`

**Step 1: Create .dockerignore file**

Create `.dockerignore` in zettelkasten-mcp root:

```
# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
.venv/
venv/
ENV/
env/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
*.cover

# Build artifacts
build/
dist/
*.egg-info/
.eggs/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Git
.git/
.gitignore
.gitattributes

# CI/CD
.github/

# Documentation (build-time not needed)
docs/
README.md
LICENSE

# Data directories (mounted as volumes)
data/
.pnotes/

# Test files
tests/
conftest.py

# Development tools
.pre-commit-config.yaml
scripts/

# UV lock file
uv.lock

# VS Code workspace
*.code-workspace

# Environment files (use at runtime)
.env
.env.example
```

**Step 2: Test build with .dockerignore**

```bash
docker build --no-cache -t zettelkasten-mcp:test .
```

Expected: Build excludes unnecessary files, faster build time

---

## Task 3: Create Docker Compose configuration

**Files:**

- Create: `docker-compose.yml`
- Create: `docker-compose.override.yml.example`

**Step 1: Create docker-compose.yml**

Create `docker-compose.yml` in zettelkasten-mcp root:

```yaml
version: '3.8'

services:
  zettelkasten:
    image: zettelkasten-mcp:latest
    container_name: zettelkasten-mcp
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped

    # Persistent storage
    volumes:
      # Mount shared notes directory
      - zettelkasten-notes:/data/notes
      # Mount database directory
      - zettelkasten-db:/data/db

    environment:
      - ZETTELKASTEN_NOTES_DIR=/data/notes
      - ZETTELKASTEN_DATABASE_PATH=/data/db/zettelkasten.db
      - ZETTELKASTEN_BASE_DIR=/data
      - ZETTELKASTEN_LOG_LEVEL=INFO
      - PYTHONUNBUFFERED=1

    # Keep container running
    stdin_open: true
    tty: true

    # Resource limits (adjust based on usage)
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

    # Logging configuration
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  zettelkasten-notes:
    driver: local
  zettelkasten-db:
    driver: local
```

**Step 2: Create development override example**

Create `docker-compose.override.yml.example`:

```yaml
# Copy this to docker-compose.override.yml for local development
version: '3.8'

services:
  zettelkasten:
    # Use bind mounts for development
    volumes:
      - ./data/notes:/data/notes
      - ./data/db:/data/db
      - ./src:/app/src  # Hot reload source code

    environment:
      - ZETTELKASTEN_LOG_LEVEL=DEBUG
```

**Step 3: Test Docker Compose**

```bash
docker-compose up -d
docker-compose ps
docker-compose logs zettelkasten
```

Expected: Container starts successfully, logs show "Starting Zettelkasten MCP server"

**Step 4: Test container persistence**

```bash
docker-compose down
docker-compose up -d
```

Expected: Data persists across container restarts

---

## Task 4: Create VS Code configuration documentation

**Files:**

- Create: `docs/DOCKER_SETUP.md`
- Modify: `README.md` (add Docker section)

**Step 1: Create Docker setup documentation**

Create `docs/DOCKER_SETUP.md`:

```markdown
# Docker Setup Guide

## Overview

This guide explains how to run the Zettelkasten MCP server as a Docker container and connect multiple VS Code instances to the shared server.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose 2.0+
- VS Code with GitHub Copilot or Claude extension
- `docker` and `docker-compose` commands available in PATH

## Quick Start

### 1. Build and Start the Container

```bash
cd /path/to/zettelkasten-mcp
docker-compose up -d
```

This creates:

- A running container named `zettelkasten-mcp`
- Persistent volumes for notes and database
- A long-running MCP server process

### 2. Verify Container is Running

```bash
docker-compose ps
docker-compose logs zettelkasten
```

Expected output: `Starting Zettelkasten MCP server`

### 3. Configure VS Code / Claude Desktop

#### For Claude Desktop (macOS)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "zettelkasten-mcp",
        "python",
        "-m",
        "zettelkasten_mcp.main"
      ]
    }
  }
}
```

#### For Claude Desktop (Linux)

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "zettelkasten-mcp",
        "python",
        "-m",
        "zettelkasten_mcp.main"
      ]
    }
  }
}
```

#### For VS Code with MCP Extension

Add to `.vscode/settings.json` or workspace settings:

```json
{
  "mcp.servers": {
    "zettelkasten": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "zettelkasten-mcp",
        "python",
        "-m",
        "zettelkasten_mcp.main"
      ]
    }
  }
}
```

### 4. Restart Claude Desktop / VS Code

Restart your client application to load the new configuration.

## Multi-User Setup

### Benefits

- **Shared knowledge base**: All users access the same notes and links
- **Single source of truth**: Database consistency across all sessions
- **Centralized backup**: One volume to backup
- **Resource efficiency**: One server process instead of N processes

### Concurrent Access

The SQLite database uses WAL (Write-Ahead Logging) mode for better concurrent access:

- Multiple readers: ✅ Supported
- Multiple writers: ⚠️ Serialized (one at a time)
- Read while writing: ✅ Supported

**Best practices:**

- Use read-heavy operations (search, get) freely
- Write operations (create, update, delete) are serialized
- Avoid long-running write operations
- Consider using structure notes to organize collaboration

## Volume Management

### Persistent Volumes (Production)

Created by Docker Compose, managed by Docker:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect zettelkasten-mcp_zettelkasten-notes

# Backup notes
docker run --rm -v zettelkasten-mcp_zettelkasten-notes:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/notes-$(date +%Y%m%d).tar.gz -C /data .

# Restore notes
docker run --rm -v zettelkasten-mcp_zettelkasten-notes:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/notes-20260226.tar.gz -C /data
```

### Bind Mounts (Development)

For local development, use bind mounts:

```bash
# Copy the override example
cp docker-compose.override.yml.example docker-compose.override.yml

# Restart with local mounts
docker-compose down
docker-compose up -d
```

Now `./data/notes` and `./data/db` are directly accessible on your host.

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs zettelkasten

# Check container status
docker inspect zettelkasten-mcp

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Permission errors

The container runs as user `zettel` (UID 1000). If you get permission errors:

```bash
# Fix volume permissions
docker-compose exec zettelkasten chown -R zettel:zettel /data
```

### VS Code can't connect

1. Verify container is running: `docker ps | grep zettelkasten`
2. Test connection manually: `docker exec -i zettelkasten-mcp python -m zettelkasten_mcp.main --help`
3. Check VS Code MCP extension logs
4. Restart VS Code completely

### Database locked errors

If you see "database is locked" errors with multiple users:

1. Verify WAL mode is enabled (it should be by default)
2. Reduce concurrent write operations
3. Consider implementing a retry mechanism in your client

### Container using too much memory

Adjust resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Reduce from 2G
```

## Maintenance

### Update the Server

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### View logs

```bash
# Follow logs
docker-compose logs -f zettelkasten

# Last 100 lines
docker-compose logs --tail=100 zettelkasten
```

### Backup data

```bash
# Automated backup script
./scripts/backup-docker-volumes.sh
```

### Stop the server

```bash
# Stop without removing volumes
docker-compose stop

# Stop and remove container (keeps volumes)
docker-compose down

# Stop and remove everything including volumes
docker-compose down -v  # ⚠️ This deletes all data!
```

## Security Considerations

### Network Isolation

The container doesn't expose any ports by default. It only communicates via `docker exec`, which requires:

- Docker socket access
- Appropriate user permissions

### File Permissions

- Container runs as non-root user (`zettel`, UID 1000)
- Volumes are owned by `zettel:zettel`
- Host access requires appropriate group membership

### Production Hardening

For production deployments:

1. Use read-only root filesystem:

   ```yaml
   services:
     zettelkasten:
       read_only: true
       tmpfs:
         - /tmp
   ```

2. Disable privilege escalation:

   ```yaml
   services:
     zettelkasten:
       security_opt:
         - no-new-privileges:true
   ```

3. Use specific image tags (not `latest`)
4. Enable automatic security updates
5. Implement proper backup strategy

## Monitoring

### Health Checks

The container includes a health check that verifies data directories exist:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' zettelkasten-mcp
```

### Resource Usage

```bash
# Real-time stats
docker stats zettelkasten-mcp

# Detailed inspection
docker inspect zettelkasten-mcp | grep -A 10 "Memory\|Cpu"
```

## Migration from Local Setup

If you're migrating from a local installation:

### 1. Backup existing data

```bash
cp -r ./data/notes ./data/notes.backup
cp -r ./data/db ./data/db.backup
```

### 2. Start Docker container

```bash
docker-compose up -d
```

### 3. Copy data into container

```bash
docker cp ./data/notes/. zettelkasten-mcp:/data/notes/
docker cp ./data/db/. zettelkasten-mcp:/data/db/

# Fix permissions
docker-compose exec zettelkasten chown -R zettel:zettel /data
```

### 4. Rebuild index

```bash
docker exec -i zettelkasten-mcp python -c "
from zettelkasten_mcp.services.zettel_service import ZettelService
service = ZettelService()
service.initialize()
service.repository.rebuild_index()
print('Index rebuilt successfully')
"
```

### 5. Update MCP client configuration

Follow the configuration steps in section 3 above.

### 6. Test connection

Open Claude Desktop or VS Code and verify you can access your notes.

## Advanced Configurations

### Custom Data Locations

To use a specific host directory:

```yaml
# docker-compose.override.yml
services:
  zettelkasten:
    volumes:
      - /mnt/shared-storage/zettelkasten-notes:/data/notes
      - /mnt/shared-storage/zettelkasten-db:/data/db
```

### Different Database Backends

While SQLite is default, you can configure for PostgreSQL:

1. Update `config.py` to support PostgreSQL URLs
2. Add PostgreSQL service to `docker-compose.yml`
3. Update environment variables

### Cluster Deployment

For high-availability:

1. Use external database (PostgreSQL with replication)
2. Mount network filesystem (NFS, GlusterFS) for notes
3. Deploy behind load balancer
4. Implement distributed locking for writes

## FAQ

**Q: Can I run multiple containers?**
A: Yes, but they should share the same volumes to have a unified knowledge base.

**Q: What happens if the container crashes?**
A: Docker Compose's `restart: unless-stopped` policy automatically restarts the container.

**Q: Can I access notes directly on the filesystem?**
A: Yes, use bind mounts (development setup) to access `./data/notes` directly.

**Q: How do I migrate to a different server?**
A: Backup volumes with `docker run` commands above, transfer files, restore on new server.

**Q: Is this production-ready?**
A: Yes, with proper backups, monitoring, and security hardening. SQLite handles modest concurrent usage well.

**Q: What's the performance overhead?**
A: Minimal. `docker exec` has negligible overhead vs direct Python execution.

```

**Step 2: Add Docker section to README.md**

Add to README.md after the "Connecting to Claude Desktop" section:

```markdown
### Using Docker (Multi-User / Shared Setup)

For shared access across multiple users or VS Code instances, run the server as a Docker container:

```bash
# Start the containerized server
docker-compose up -d

# Configure your client
# Edit Claude Desktop config or VS Code settings
{
  "mcpServers": {
    "zettelkasten": {
      "command": "docker",
      "args": ["exec", "-i", "zettelkasten-mcp", "python", "-m", "zettelkasten_mcp.main"]
    }
  }
}
```

See [Docker Setup Guide](docs/DOCKER_SETUP.md) for detailed instructions on:

- Container setup and configuration
- Multi-user concurrent access
- Volume management and backups
- Troubleshooting and maintenance
- Production deployment

```

**Step 3: Test documentation instructions manually**

Follow the documentation steps to verify they work correctly.

Expected: Users can successfully deploy and connect to the dockerized server.

---

## Task 5: Create backup script

**Files:**
- Create: `scripts/backup-docker-volumes.sh`

**Step 1: Create backup script**

Create `scripts/backup-docker-volumes.sh`:

```bash
#!/usr/bin/env bash
# Backup Zettelkasten Docker volumes

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="${CONTAINER_NAME:-zettelkasten-mcp}"

echo "🔄 Starting Zettelkasten backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup notes volume
echo "📝 Backing up notes..."
docker run --rm \
  -v zettelkasten-mcp_zettelkasten-notes:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine \
  tar czf "/backup/notes_${TIMESTAMP}.tar.gz" -C /data .

# Backup database volume
echo "💾 Backing up database..."
docker run --rm \
  -v zettelkasten-mcp_zettelkasten-db:/data \
  -v "$(pwd)/$BACKUP_DIR":/backup \
  alpine \
  tar czf "/backup/db_${TIMESTAMP}.tar.gz" -C /data .

# Calculate sizes
NOTES_SIZE=$(du -h "$BACKUP_DIR/notes_${TIMESTAMP}.tar.gz" | cut -f1)
DB_SIZE=$(du -h "$BACKUP_DIR/db_${TIMESTAMP}.tar.gz" | cut -f1)

echo "✅ Backup complete!"
echo "   Notes: $BACKUP_DIR/notes_${TIMESTAMP}.tar.gz ($NOTES_SIZE)"
echo "   DB:    $BACKUP_DIR/db_${TIMESTAMP}.tar.gz ($DB_SIZE)"

# Optional: Clean up old backups (keep last 7 days)
if [[ "${CLEANUP_OLD:-true}" == "true" ]]; then
  echo "🧹 Cleaning up backups older than 7 days..."
  find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
fi

echo "🎉 Done!"
```

**Step 2: Make script executable**

```bash
chmod +x scripts/backup-docker-volumes.sh
```

**Step 3: Test backup script**

```bash
./scripts/backup-docker-volumes.sh
ls -lh backups/
```

Expected: Backup files created successfully

---

## Task 6: Add SQLite WAL mode configuration

**Files:**

- Modify: `src/zettelkasten_mcp/models/db_models.py`

**Step 1: Update database initialization for WAL mode**

In `src/zettelkasten_mcp/models/db_models.py`, find the `init_db()` function and update:

```python
def init_db() -> None:
    """Initialize the database schema."""
    try:
        engine = get_engine()

        # Enable WAL mode for better concurrent access
        if str(engine.url).startswith('sqlite'):
            with engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.execute(text("PRAGMA busy_timeout=5000"))
                conn.commit()

        Base.metadata.create_all(engine)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
```

**Step 2: Run tests to verify WAL mode**

```bash
cd /home/kaesmad/projects/external/zettelkasten-mcp
uv run pytest tests/test_note_repository.py -v
```

Expected: All tests pass with WAL mode enabled

**Step 3: Commit changes**

```bash
git add src/zettelkasten_mcp/models/db_models.py
git commit -m "feat: enable SQLite WAL mode for concurrent access"
```

---

## Task 7: Create CI/CD workflow for Docker

**Files:**

- Create: `.github/workflows/docker-build.yml`

**Step 1: Create Docker build workflow**

Create `.github/workflows/docker-build.yml`:

```yaml
name: Docker Build and Test

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'src/**'
      - 'Dockerfile'
      - 'docker-compose.yml'
      - '.github/workflows/docker-build.yml'
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  docker-build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: false
          tags: zettelkasten-mcp:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Start container
        run: |
          docker-compose up -d
          sleep 5

      - name: Test container health
        run: |
          docker ps | grep zettelkasten-mcp
          docker-compose logs zettelkasten
          docker inspect --format='{{.State.Health.Status}}' zettelkasten-mcp

      - name: Test MCP server
        run: |
          docker exec zettelkasten-mcp python -c "
          from zettelkasten_mcp.services.zettel_service import ZettelService
          service = ZettelService()
          service.initialize()
          print('✅ MCP server initialized successfully')
          "

      - name: Cleanup
        if: always()
        run: docker-compose down -v
```

**Step 2: Commit workflow**

```bash
git add .github/workflows/docker-build.yml
git commit -m "ci: add Docker build and test workflow"
```

---

## Task 8: Test full Docker deployment

**Files:**

- None (testing task)

**Step 1: Clean slate deployment test**

```bash
# Clean everything
cd /home/kaesmad/projects/external/zettelkasten-mcp
docker-compose down -v
rm -rf ./data/notes/* ./data/db/*

# Build and start
docker-compose build --no-cache
docker-compose up -d

# Wait for startup
sleep 5
```

Expected: Container starts successfully

**Step 2: Test MCP operations**

```bash
# Create a test note
docker exec -i zettelkasten-mcp python -c "
from zettelkasten_mcp.services.zettel_service import ZettelService
from zettelkasten_mcp.models.schema import NoteType

service = ZettelService()
service.initialize()

note = service.create_note(
    title='Docker Test Note',
    content='This note was created via Docker container',
    note_type=NoteType.FLEETING,
    tags=['test', 'docker']
)
print(f'✅ Created note: {note.id}')

# Verify it was created
notes = service.search_notes(tags=['docker'])
print(f'✅ Found {len(notes)} note(s) with docker tag')
"
```

Expected: Note created and searchable

**Step 3: Test persistence**

```bash
# Restart container
docker-compose restart

# Verify data persists
docker exec -i zettelkasten-mcp python -c "
from zettelkasten_mcp.services.zettel_service import ZettelService

service = ZettelService()
service.initialize()

notes = service.search_notes(tags=['docker'])
print(f'✅ After restart: Found {len(notes)} note(s) with docker tag')
assert len(notes) > 0, 'Data did not persist!'
"
```

Expected: Data persists across restarts

**Step 4: Test multi-session access**

Open two terminals and run simultaneously:

Terminal 1:

```bash
docker exec -i zettelkasten-mcp python -c "
from zettelkasten_mcp.services.zettel_service import ZettelService
import time

service = ZettelService()
service.initialize()

for i in range(5):
    note = service.create_note(
        title=f'User 1 Note {i}',
        content=f'Created by user 1',
        note_type='fleeting',
        tags=['user1']
    )
    print(f'User 1 created: {note.id}')
    time.sleep(1)
"
```

Terminal 2:

```bash
docker exec -i zettelkasten-mcp python -c "
from zettelkasten_mcp.services.zettel_service import ZettelService
import time

service = ZettelService()
service.initialize()

for i in range(5):
    note = service.create_note(
        title=f'User 2 Note {i}',
        content=f'Created by user 2',
        note_type='fleeting',
        tags=['user2']
    )
    print(f'User 2 created: {note.id}')
    time.sleep(1)
"
```

Expected: Both complete successfully without database lock errors

---

## Task 9: Update project documentation

**Files:**

- Modify: `README.md` (add Docker section link)
- Modify: `docs/VS_CODE_SETUP.md` (add Docker instructions)

**Step 1: Update README.md Installation section**

After the existing installation section, add:

```markdown
## Docker Installation (Recommended for Multi-User)

For shared access across multiple users/workspaces:

```bash
# Build and start the container
docker-compose up -d

# Verify it's running
docker-compose ps
```

Configure your MCP client:

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "docker",
      "args": ["exec", "-i", "zettelkasten-mcp", "python", "-m", "zettelkasten_mcp.main"]
    }
  }
}
```

📖 **Full guide:** [Docker Setup Documentation](docs/DOCKER_SETUP.md)

Benefits:

- ✅ Shared knowledge base across all users
- ✅ Single source of truth
- ✅ Centralized backups
- ✅ Efficient resource usage

```

**Step 2: Add Docker note to VS_CODE_SETUP.md**

At the top of `docs/VS_CODE_SETUP.md`, add:

```markdown
> **💡 Multi-User Setup:** For shared access across multiple VS Code instances, see [Docker Setup Guide](DOCKER_SETUP.md).

---
```

**Step 3: Commit documentation updates**

```bash
git add README.md docs/VS_CODE_SETUP.md
git commit -m "docs: add Docker installation and multi-user setup instructions"
```

---

## Implementation Complete

### Summary

You now have:

1. ✅ **Dockerfile**: Multi-stage build with security best practices
2. ✅ **Docker Compose**: Easy deployment with persistent volumes
3. ✅ **Documentation**: Comprehensive setup and troubleshooting guide
4. ✅ **Backup Scripts**: Automated volume backup and restore
5. ✅ **Concurrent Access**: SQLite WAL mode for better multi-user support
6. ✅ **CI/CD**: Automated Docker build and test workflow
7. ✅ **Testing**: Verified deployment and multi-session access

### Next Steps

**For immediate use:**

```bash
# Start the server
docker-compose up -d

# Configure Claude Desktop / VS Code
# (Follow docs/DOCKER_SETUP.md)

# Test it works
docker exec -i zettelkasten-mcp python -m zettelkasten_mcp.main --help
```

**For production:**

1. Review security settings in docker-compose.yml
2. Set up automated backups (cron job running backup script)
3. Configure monitoring (Prometheus + Grafana)
4. Implement proper logging aggregation
5. Document your disaster recovery procedures

### Rollback Plan

If issues occur:

```bash
# Stop Docker version
docker-compose down

# Revert to local installation
source .venv/bin/activate
python -m zettelkasten_mcp.main
```

Your data is safe in Docker volumes and can be exported/imported as needed.
