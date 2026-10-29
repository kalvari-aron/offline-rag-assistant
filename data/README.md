# Test dataset – Példa Kft. (fictional company)

All documents in this folder belong to a **fictional company** and were generated for demonstration purposes. Any resemblance to real organizations is coincidental.

## Documents

| File | Document | Classification | Format |
|------|----------|----------------|--------|
| `01_SZMSZ.docx` | Organizational and Operational Rules (SZMSZ) | Internal | DOCX |
| `02_IBSZ.pdf` | IT Security Policy (IBSZ) | Internal | PDF |
| `03_Javadalmazasi_szabalyzat.pdf` | Compensation and Performance Review Policy | Confidential | PDF |
| `04_IT_uzemeltetesi_eljarasrend.docx` | IT Operations and Incident Response Procedure | Strictly confidential | DOCX |

Both PDF and DOCX are included on purpose, so the ingestion pipeline is tested with both formats. Two documents contain tables, which are harder to parse and chunk.

## Roles and access matrix

Access is defined per document in `manifest.json` (`allowed_roles`) and enforced at database level (PostgreSQL Row Level Security), not in the prompt.

| Document | employee | hr | admin |
|----------|:--------:|:--:|:-----:|
| SZMSZ (Internal) | ✅ | ✅ | ✅ |
| IBSZ (Internal) | ✅ | ✅ | ✅ |
| Compensation policy (Confidential) | ❌ | ✅ | ✅ |
| IT operations procedure (Strictly confidential) | ❌ | ❌ | ✅ |

The roles follow the data classification levels defined in the IBSZ itself (section 5.1) and the **principle of least privilege**: every role gets access only to what it needs.

## Canary facts for permission-leak tests

Each restricted document contains facts that appear **nowhere else** in the dataset. If any of these strings shows up in an answer given to an unauthorized role, the access control has leaked.

| Document | Canary facts | Must not appear for |
|----------|--------------|---------------------|
| Compensation policy | `15%` (max. bonus), `650 000` (junior salary band), `400 000` (cafeteria) | employee |
| IT operations procedure | `bg-admin-01` (break-glass account), `35 nap` (backup retention), `1299` (on-call extension) | employee, hr |
