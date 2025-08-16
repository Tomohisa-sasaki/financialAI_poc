
# Backend
Run:
```
pip install -r requirements.txt
uvicorn apps.api.main:app --reload --port 8000
```

Auth: HTTP Basic via env `API_USER` / `API_PASSWORD`.
Endpoints:
- GET /health
- GET /jq/statements
- GET /edinet/list
- GET /edinet/parse
- POST /analysis/timeseries
- POST /analysis/chart.png
- POST /report/pdf
- POST /report/email
- GET /companies/search
- POST /ai/ask
