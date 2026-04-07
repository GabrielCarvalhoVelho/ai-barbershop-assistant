from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.company import Company
from app.models.enums import DocumentCategory
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User

logger = get_logger(__name__)

SEED_DOCUMENTS = [
    {
        "title": "Corte masculino",
        "content": (
            "Corte masculino tradicional — R$ 40,00. "
            "Tempo estimado: 30 minutos. Inclui lavagem."
        ),
        "category": DocumentCategory.SERVICES,
    },
    {
        "title": "Barba completa",
        "content": (
            "Barba completa com toalha quente e pós-barba — R$ 30,00. "
            "Tempo estimado: 20 minutos."
        ),
        "category": DocumentCategory.SERVICES,
    },
    {
        "title": "Corte + Barba",
        "content": (
            "Combo corte masculino + barba completa — R$ 60,00 "
            "(economia de R$ 10). Tempo estimado: 45 minutos."
        ),
        "category": DocumentCategory.SERVICES,
    },
    {
        "title": "Sobrancelha",
        "content": (
            "Design de sobrancelha masculina — R$ 15,00. "
            "Tempo estimado: 10 minutos."
        ),
        "category": DocumentCategory.SERVICES,
    },
    {
        "title": "Horário de funcionamento",
        "content": (
            "Segunda a sexta: 9h às 19h. "
            "Sábado: 8h às 17h. "
            "Domingo e feriados: fechado."
        ),
        "category": DocumentCategory.HOURS,
    },
    {
        "title": "Agendamento",
        "content": (
            "Agendamentos podem ser feitos por mensagem ou presencialmente. "
            "Recomendamos agendar com pelo menos 1 dia de antecedência."
        ),
        "category": DocumentCategory.POLICIES,
    },
    {
        "title": "Cancelamento",
        "content": (
            "Cancelamentos devem ser feitos com no mínimo 2 horas de antecedência. "
            "Faltas sem aviso podem resultar em prioridade reduzida no próximo agendamento."
        ),
        "category": DocumentCategory.POLICIES,
    },
    {
        "title": "Formas de pagamento",
        "content": (
            "Aceitamos dinheiro, Pix e cartões de débito e crédito. "
            "Não trabalhamos com fiado."
        ),
        "category": DocumentCategory.POLICIES,
    },
    {
        "title": "Preciso agendar?",
        "content": (
            "O atendimento é preferencialmente por agendamento, "
            "mas aceitamos encaixes quando há disponibilidade."
        ),
        "category": DocumentCategory.FAQ,
    },
    {
        "title": "Tem estacionamento?",
        "content": (
            "Não temos estacionamento próprio, "
            "mas há estacionamento público na rua ao lado."
        ),
        "category": DocumentCategory.FAQ,
    },
    {
        "title": "Sobre a barbearia",
        "content": (
            "A Barbearia Dev é especializada em cortes masculinos "
            "modernos e clássicos. Ambiente climatizado e confortável."
        ),
        "category": DocumentCategory.GENERAL,
    },
]


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
    await session.flush()

    for doc_data in SEED_DOCUMENTS:
        doc = KnowledgeDocument(
            company_id=company.id,
            title=doc_data["title"],
            content=doc_data["content"],
            category=doc_data["category"],
        )
        session.add(doc)

    await session.commit()

    logger.info(
        "Seed concluído: company_id=%s user_id=%s documents=%s",
        company.id,
        user.id,
        len(SEED_DOCUMENTS),
    )
