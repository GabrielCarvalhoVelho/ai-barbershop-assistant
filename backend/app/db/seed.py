from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.company import Company
from app.models.user import User

logger = get_logger(__name__)


async def seed_dev_data(session: AsyncSession) -> None:
    """Cria dados mínimos para desenvolvimento. Idempotente."""

    result = await session.execute(select(Company).limit(1))
    if result.scalars().first() is not None:
        logger.info("Seed ignorado: dados já existem.")
        return

    company = Company(
        name="Barbearia Dev",
        address="Rua Exemplo, 123",
        phone="+5511999999999",
    )
    session.add(company)
    await session.flush()

    user = User(
        company_id=company.id,
        name="Cliente Teste",
        phone="+5511900000000",
        email="teste@barbershop.dev",
    )
    session.add(user)
    await session.commit()

    logger.info(
        "Seed concluído: company_id=%s user_id=%s",
        company.id,
        user.id,
    )
