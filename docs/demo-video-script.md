# Demo Video Script

Length target: 90 to 120 seconds.

## Scene 1

Show stack boot and supplier registry list.

Narration:
This project is a controlled finance workflow agent. It analyzes incoming invoices, checks suppliers, detects duplicates, suggests category, creates only a draft pre-entry, and waits for human approval.

## Scene 2

Upload `aws_invoice.txt`.

Narration:
The agent extracts structured fields, runs validated tools, calculates confidence, and creates a draft with full audit trail.

## Scene 3

Open waiting approval run.

Narration:
Approval screen shows extracted fields, supplier match, duplicate signals, confidence, and every tool execution before any final decision.

## Scene 4

Approve normal scenario, then upload `duplicate_invoice.txt`.

Narration:
Safe path approves the draft. Duplicate path stays controllable and pushes the reviewer to reject or edit instead of acting blindly.

## Scene 5

Resume with edit on ambiguous supplier case.

Narration:
The workflow resumes from checkpoint, updates the draft, and finishes without rerunning side effects.
