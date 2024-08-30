# Database migration from Postgres version 13 to 16

Unfortunately, this process can't be fully automated, therefore manual work is required. With the new update, a new database container `taranis-ng-postgres-1` is created, and you only need to transfer data from the old container `taranis-ng-database-1` to the new one. This approach keeps your old database container intact if the migration fails, allowing you to revert the change if necessary. If the migration is successful, you can delete the old container.

## Database update
Edit your `.env` file and change variable `POSTGRES_TAG` from `13-alpine` to `16-alpine`:
```
POSTGRES_TAG=16-alpine
```

Update (pulling images or building from Git):

```
docker compose -f docker/docker-compose.yml pull
```
or on Windows:
```
docker compose -f docker\docker-compose.yml build
```

Run containers with:

```
docker compose -f docker/docker-compose.yml up --no-build -d
```
or on Windows:
```
docker compose -f docker\docker-compose.yml up --no-build -d
```

The new `taranis-ng-postgres-1` container has been created.

## Migration

### 1. Backup database
Get into `taranis-ng-database-1` container shell:

```
docker exec -it taranis-ng-database-1 /bin/sh
```

Run inside the `taranis-ng-database-1` container to create a backup:
```
pg_dump -U taranis-ng -d taranis-ng -Z 9 --clean > db_bak.gz
exit
```

The backup file has been created in the container and you should be back in the host shell.

### 2. Copy backup to local machine
Now let's copy the backup file from the container to the host. The backup file `db_bak.gz` will appear in the current directory:

```
docker cp taranis-ng-database-1:/db_bak.gz db_bak.gz
```

### 3. Copy backup to the new `taranis-ng-postgres-1` container
The backup file must be in the current directory:

```
docker cp db_bak.gz taranis-ng-postgres-1:/db_bak.gz
```

Now the backup is inside the new container.

### 4. Restore Data
Stop the `taranis-ng-core-1` container:

```
docker stop taranis-ng-core-1
```

Get inside the new `taranis-ng-postgres-1` container:

```
docker exec -it taranis-ng-postgres-1 /bin/sh
```

Now let's restore the backup. The backup file must be in the current directory:

```
zcat db_bak.gz | psql -U taranis-ng -d taranis-ng
exit
```

Start the `taranis-ng-core-1` container:

```
docker start taranis-ng-core-1
```

If there are no errors in the output log, you can stop the old `taranis-ng-database-1` container:

```
docker stop taranis-ng-database-1
```

Check if everything runs correctly. After some time, you can delete the old `taranis-ng-database-1` container.

If there are any issues, you can revert and use the old `taranis-ng-database-1` container by mapping it back in `docker-compose.yml` (see below for configuration changes).

## Configuration Changes

### Before (v13)

File `.env` modified line:

```
POSTGRES_TAG=13-alpine
```

File `docker-compose.yml` modified lines:

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

### After (v16)

File `.env` modified line:

```
POSTGRES_TAG=16-alpine
```

File `docker-compose.yml` modified lines:

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
