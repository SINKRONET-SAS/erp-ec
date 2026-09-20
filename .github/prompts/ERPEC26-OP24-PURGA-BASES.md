# ERPEC26-OP24 — Purga de bases y roles de ensayo

Objetivo: eliminar las bases y roles de PostgreSQL residuales de pruebas sin tocar las instancias reales.
Fuente de verdad: scripts/purge-test-databases.py y docs/OPERACION_LOCAL.md. Evidencia: docs/evidencias/ERPEC26-OP24-PURGA-BASES-20260920.json.
Reglas: simulación primero, solo con autorización expresa del titular, nunca borrar erpec_fundador, erpec_demo, erpec_a, erpec_b ni postgres.
