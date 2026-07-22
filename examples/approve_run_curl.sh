curl -X POST "http://localhost:8000/api/v1/agent-runs/1/resume" \
  -H "Authorization: Bearer change-me" \
  -H "X-Organization-Slug: acme-finance" \
  -H "X-User-Email: ana@acme.demo" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "notes": "Looks correct"
  }'
