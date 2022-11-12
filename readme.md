# Сontent management and customer interaction system (CM-CIS)
It includes a telegram bot for interacting with clients and a web application* for content management.

*not implemented yet

## Deploy
Clone this repository to your server with command:
```bash
git clone https://github.com/j2cry/cmcis.git
```

Create `.env` file in project root and define required variables in it:
```
DBHOST=...
DBPORT=...
DBNAME=...
SCHEMA=...
TGTOKEN=...

PSQL_MASTER_USER=...
PSQL_MASTER_PASSWORD=...

PSQL_HANDLER_USER=...
PSQL_HANDLER_PASSWORD=...

PSQL_USER=...
PSQL_PASSWORD=...
```

Then, start up with docker-compose:
```bash
docker-compose up pginit
docker-compose up -d
```

## Structure
### Files & folders
`custom-postgres` - PostgreSQL docker container with gettext package installed<br>
`pgdata` - default folder for SQL data<br>
`reports` - service folder for sending files<br>
`sql` - database initialization scripts: here must be a script which initializes required schema and structure<br>
`keystore.py` - utility for setting up passwords inside containers<br>


### Database
<img src="sql/cmcis-erd.png" alt="Look for ERD if `sql` folder">
