# Casa-Bot: Real Estate SMS Bot

Casa-Bot is a real estate SMS bot built using FastAPI, Twilio, LangChain, and Docker. It enables users to interact via SMS messages, book appointments, and perform various real estate-related tasks.

## Project Structure

```plaintext
.
├── .vscode
│   └── easycode.ignore
├── services
│   ├── api
│   │   ├── toolset
│   │   │   └── mongo_db.py
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── requirements.txt
│   └── traefik
│       ├── traefik.dev.toml
│       └── traefik.prod.toml
├── .gitignore
├── README.md
├── docker-compose.prod.yml
├── docker-compose.yml
└── traefik
    └── traefik.toml
```
# Build and run development environment
docker-compose up --build

# Test API ping endpoint
curl -H "Host: fastapi.localhost" http://0.0.0.0:81/ping

```
curl -X POST "http://0.0.0.0:81/only-for-testing-agent" \
     -H "Host: fastapi.localhost" \
     -H "Content-Type: application/json" \
     -d '{
           "message": {
             "phone_number": "123456789",
             "text_message": "Hello, this is a test message"
           },
           "password": "BadMotherfucker"
         }'

```

# Stop development environment
```docker-compose down
```

# Build and run production environment
```docker-compose -f docker-compose.prod.yml up --build
```
# Test production environment
```curl https://subdomain.example.com
```
# Stop production environment
```docker-compose -f docker-compose.prod.yml down
```
