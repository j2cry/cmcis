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

SERVICE_INTERVAL=7 day
ACTUAL_INTERVAL=1 hour
MAXBOOK=2
BOT_ADMIN_ID=...
RELATED_CHANNEL=...
```

Then, start up with docker-compose:
```bash
docker-compose up pginit
docker-compose up -d
```

## Settings
The settings are available in a file `my.cnf` that is mostly generated automatically.
Here are described some predefined parameters, that you can change manually
```bash
[BOT]
timeout=300     # conversation session timeout (in seconds)
```



## Structure
### Files & folders
`postgres-init` - container with gettext package installed for `init.sql` compiling<br>
`pgdata` - default folder for SQL data<br>
`reports` - service folder for sending files<br>
`sql` - database initialization scripts: here must be a script which initializes required schema and structure<br>
`keystore.py` - utility for setting up passwords inside containers<br>


### Database
<img src="sql/cmcis-erd.png" alt="Look for ERD if `sql` folder">

Key poiints
* activities are not displayed at all if the value of `showtime` or `openreg` is NULL
* activities are not displayed at all if the value of `active` is NULL or FALSE
* activities are displayed in the service menu for 7 days after the showtime; this behavior is hardcoded