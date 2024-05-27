# Cackalackycon - Score Processor

### Env
We transitioned to doppler to handle secrets, but the first iteration was used with a .env file.

### Environment Variables
| Env Name               | Description                    | Example              |
|------------------------|--------------------------------|----------------------|
| APP_NAME               | name of the app                | game-event-processor |
| APP_ENV                | the application environment    | dev, test, prod, etc |
| AWS_LOGGER_ACCESS_KEY  | s3 IAM access key              | ...                  |
| AWS_LOGGER_SECRET_KEY  | s3 IAM access secret           | ...                  |
| OTEL_COLLECTOR_SVC     | metrics collector service name | otel-container       |
| PG_DB_HOST             | postgres host name             | localhost            |
| PG_DB_USER             | db user                        | ckc_user             |
| PG_DB_PASSWORD         | db user password               | somethingClever      |
| PG_DB_PORT             | port for the postgres db       | 5432                 |
| PG_DB_DATABASE         | postgres database              | cackalacky           |
| PG_DB_CONNECTION_LIMIT | connection limit               | 10                   |
| REDIS_HOST             | redis service name             | redis-container      |
| SKIP_METRICS           | Boolean to send to otel or not | False                |


## Non Docker

### Create virtualenv first
```bash
pip install virtualenv
virtualenv -p python3 scoreprocessor
. .\scoreprocessor\Scripts\activate
```

### Install requirements
```bash
pip install -r requirements.txt
```

### Run the Processor

#### With Doppler
```
doppler secrets set SKIP_METRICS=False
doppler run -- python processor.py --log-config log.ini
```

#### Without Doppler
You'll have to set variables prior to running. So either set them inline, or export.
```
SKIP_METRICS=True python processor.py --log-config log.ini
```


### Build the image
``docker build -t score-processor:latest .``

### Start the container

``docker run --name score-processor -e DOPPLER_TOKEN="<token>" --network local-ckc``

### Stop the container
``docker stop score-processor``

### Remove the container
``docker rm score-processor``

### Access the container
``docker exec -it score-processor /bin/bash``

# Network

To communicate with local otel collector, create a docker network:
docker network create local-ckc

Then, run the containers with your network:
--network local-ckc

# Valid messages

When it's a list of dict, we expect the game key "g" to be the full name of the game
When it's a list of list, we expect either an abbreviation or the full name

```python
GAME_ABBREVIATION_MAP = {
    "BO": "Breakout",
    "LA": "Labyrinth",
    "RO": "Asteroids",
    "TT": "Tappytime",
}
```


```bash
PUBLISH high-score-processor "{\"user_uuid\": \"b4958y\", \"mac_address\": \"484jjg\", \"event\": \"high-score\", \"high_scores\": [{\"g\": \"Tappytime\", \"s\": \"2000\", \"d\": \"1000\"}]}"
PUBLISH high-score-processor "{\"user_uuid\": \"b4958y\", \"mac_address\": \"484jjg\", \"event\": \"high-score\", \"high_scores\": [[\"TT\", \"2000\", \"1000\"]]}"
PUBLISH high-score-processor "{\"user_uuid\": \"b4958y\", \"mac_address\": \"484jjg\", \"event\": \"high-score\", \"high_scores\": [[\"Tappytime\", \"2000\", \"1000\"]]}"
PUBLISH high-score-processor "{\"user_uuid\": \"121a92f9-7dfe-f37b-7ea9-c41b1ecc08a6\", \"mac_address\": \"34:94:54:89:BE:49\", \"event\": \"challenge-check\", \"score_id\": 6353}"
PUBLISH high-score-processor "{\"user_uuid\": \"bdd55a61-a287-6fd1-4dd8-2a793b77880f\", \"mac_address\": \"80:64:6F:92:FA:E2\", \"event\": \"challenge-check\", \"score_id\": 6122}"
```

# Formatting

isort: ``isort .``
black: ``black .``

Configs are found in: pyproject.toml