curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer change-me" \
  -H "X-Organization-Slug: acme-finance" \
  -H "X-User-Email: ana@acme.demo" \
  -F "title=AWS July Invoice" \
  -F "tags=cloud,invoice" \
  -F "idempotency_key=aws-july-001" \
  -F "file=@demo_data/documents/acme-finance/aws_invoice.txt;type=text/plain"
