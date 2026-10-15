import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def check():
    engine = create_async_engine(settings.database_url.get_secret_value(), echo=False)
    async with engine.connect() as conn:
        row = (await conn.execute(text("SELECT current_database(), current_user"))).fetchone()
        print(f"Database : {row[0]}")
        print(f"User     : {row[1]}")

        tables = (await conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"))).scalar()
        print(f"Tables   : {tables} tabel")

        users = (await conn.execute(text("SELECT count(*) FROM users"))).scalar()
        print(f"Users    : {users} user")

        docs = (await conn.execute(text("SELECT ingest_status, count(*) FROM documents GROUP BY ingest_status"))).fetchall()
        if docs:
            for status, count in docs:
                print(f"Docs     : {count} dokumen [{status}]")
        else:
            print("Docs     : 0 dokumen")

        chunks = (await conn.execute(text("SELECT count(*) FROM document_chunks"))).scalar()
        print(f"Chunks   : {chunks} chunk")

        embeddings = (await conn.execute(text("SELECT count(*) FROM document_embeddings"))).scalar()
        print(f"Embeddings: {embeddings} vektor")

    await engine.dispose()
    print("\nKoneksi .env -> PostgreSQL: OK")

asyncio.run(check())
