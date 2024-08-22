# Database Migration from Postgres Version 13 to 16

This process can't be fully automated, so some manual work is required. With the new update, a new database container `postgres` is created, and you just need to transfer data from the old container to the new one. This approach keeps your old container intact in case the migration fails, allowing you to revert back if necessary. If the migration is successful, you can delete the old container.

## Ordinary Update
Edit your local `.env` file and change this line, increasing the version from `13` to `16`:
```
POSTGRES_TAG=13-alpine
```

After the usual update (pulling images or building from Git):

```
docker compose -f docker/docker-compose.yml pull
or
docker compose -f docker\docker-compose.yml build
```

And running containers with:

```
docker compose -f docker\docker-compose.yml up --no-build -d
```

The new `postgres` container is created.

## Migration

### 1. Backup Data
Run inside the old `database` container:

```
pg_dump -U taranis-ng -d taranis-ng -Z 9 --clean > db_bak.gz
```

### 2. Copy Backup to Local
Run locally. The backup file `db_bak.gz` will appear in the current directory:

```
docker cp taranis-ng-database-1:/db_bak.gz db_bak.gz
```

### 3. Copy Backup to the New `postgres` Container
Run locally. The backup file must be in the current directory:

```
docker cp db_bak.gz taranis-ng-postgres-1:/db_bak.gz
```

### 4. Restore Data
Stop the `core` container:

```
docker stop taranis-ng-core-1
```

Run inside the new `postgres` container. The backup file must be in the current directory:

```
zcat db_bak.gz | psql -U taranis-ng -d taranis-ng
```

Start the `core` container:

```
docker start taranis-ng-core-1
```

If there are no errors in the output log, you can stop the old `database` container:

```
docker stop taranis-ng-database-1
```

Check if everything runs correctly. After some time, you can delete the old `database` container.

If there are any issues, you can revert back and use the old `database` container by mapping it back in `docker-compose.yml` (see below for configuration changes).

## Configuration Changes

### Before (v13)

File `.env`, only modified lines:

```
POSTGRES_TAG=13-alpine
```

File `docker-compose.yml`, only modified lines:

```
database:
    volumes:
      - "database_data:/var/lib/postgresql/data"

  core:
    depends_on:
      - "database"
    environment:
      DB_URL: "database"
      
  volumes:
    database:
```

### After (v16, already applied in this update)

File `.env`, only modified lines:

```
POSTGRES_TAG=16-alpine
```

File `docker-compose.yml`, only modified lines:

```
postgres:
    volumes:
      - "postgres_data:/var/lib/postgresql/data"

  core:
    depends_on:
      - "postgres"
    environment:
      DB_URL: "postgres"
      
  volumes:
    postgres:
```
