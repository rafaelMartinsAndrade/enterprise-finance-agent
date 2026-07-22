# Enterprise Finance Agent Architecture

```mermaid
flowchart LR
    U["Finance user"] --> UI["Streamlit approval UI"]
    UI --> API["FastAPI API"]
    U --> API
    API --> AUTH["Tenant auth headers"]
    API --> DOC["Document service"]
    DOC --> FILES["Tenant file storage"]
    DOC --> RUN["Workflow service"]
    RUN --> LG["LangGraph StateGraph"]
    LG --> EX["Structured extraction provider"]
    LG --> SUP["Supplier lookup tool"]
    LG --> DUP["Duplicate check tool"]
    LG --> CAT["Category suggestion tool"]
    LG --> DRAFT["Draft pre-entry tool"]
    LG --> HITL["interrupt() human review"]
    HITL --> API
    RUN --> DB["PostgreSQL app tables"]
    RUN --> CKPT["SQLite checkpoints"]
```

## Notes

- Autonomy stops at draft creation. No irreversible posting happens automatically.
- `interrupt()` plus SQLite checkpointing gives pause and resume across sessions.
- Every tool call is audited with args, result, duration, and error.
