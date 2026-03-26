import os
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config.setting import settings


def _ensure_sqlite_dir(sqlite_url: str) -> None:
    # sqlite+aiosqlite:///./data/app.db  -> ensure ./data exists
    if "sqlite" not in sqlite_url:
        return
    marker = "///"
    if marker not in sqlite_url:
        return
    path = sqlite_url.split(marker, 1)[1]
    if not path:
        return
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


_ensure_sqlite_dir(settings.SQLITE_URL)

engine: AsyncEngine = create_async_engine(
    settings.SQLITE_URL,
    future=True,
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

