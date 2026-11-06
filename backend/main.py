import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
try:
    from .auth import build_auth
except ImportError:
    from auth import build_auth


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "")
TABLE_NAME = os.getenv("MEDIUM_TABLE", "public.mediuns")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
# Render supplies this HTTPS origin; custom domains can be added via CORS_ORIGINS.
if os.getenv('RENDER_EXTERNAL_URL'):
    CORS_ORIGINS.append(os.environ['RENDER_EXTERNAL_URL'].rstrip('/'))

app = FastAPI(title="Casa da Vovó Joaquina API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serializable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", errors="replace")
    return value


def quote_identifier(identifier: str) -> str:
    if not identifier.replace("_", "").replace(".", "").isalnum():
        raise HTTPException(status_code=400, detail="Identificador de tabela inválido.")
    parts = identifier.split(".")
    return ".".join(f'"{part}"' for part in parts)


def db_connection():
    if not DATABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL não configurada. Consulte backend/.env.example.",
        )
    return psycopg.connect(DATABASE_URL, connect_timeout=15)


auth_router, current_user = build_auth(db_connection)
app.include_router(auth_router)


@app.middleware('http')
async def protect_requests(request: Request, call_next):
    if request.url.path.startswith('/api') and request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        if request.headers.get('origin') not in CORS_ORIGINS:
            return JSONResponse({'detail': 'Origem não autorizada.'}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": "configured" if DATABASE_URL else "not-configured"}


@app.get("/api/mediums", dependencies=[Depends(current_user)])
def list_mediums(search: str = Query(default="", max_length=120)) -> dict[str, Any]:
    table = quote_identifier(TABLE_NAME)
    with db_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                tuple(
                    TABLE_NAME.split(".", 1)
                    if "." in TABLE_NAME
                    else ("public", TABLE_NAME)
                ),
            )
            columns = [row["column_name"] for row in cursor.fetchall()]

            safe_columns = [col for col in columns if col.replace("_", "").isalnum()]
            where_sql = ""
            params: list[Any] = []
            if search:
                text_columns = safe_columns[:8]
                if text_columns:
                    where_sql = " WHERE " + " OR ".join(
                        f'CAST("{column}" AS TEXT) ILIKE %s' for column in text_columns
                    )
                    params = [f"%{search}%"] * len(text_columns)

            cursor.execute(
                f'SELECT * FROM {table}{where_sql} LIMIT 200',
                params,
            )
            rows = cursor.fetchall()

    return {
        "columns": safe_columns,
        "items": [
            {key: serializable(value) for key, value in row.items()}
            for row in rows
        ],
    }
