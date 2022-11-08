# Сontent management and customer interaction system (CM-CIS)
It includes a telegram bot for interacting with clients and a web application for content management.

## Deploy
Setup required environment variables in `.env` file:
```
PSQL_MASTER_USER=...
PSQL_MASTER_PASSWORD=...

PSQL_HANDLER_USER=...
PSQL_HANDLER_PASSWORD=...

PSQL_USER=...
PSQL_PASSWORD=...
```

And then start up with docker-compose:
```bash
docker-compose up pginit
docker-compose up -d
```

## Structure
### Files & folders
`botpostgres` - PostgreSQL docker container with gettext package installed<br>
`pgdata` - default folder for SQL data<br>
`sql` - database initialization scripts<br>


### Database



## Error codes
