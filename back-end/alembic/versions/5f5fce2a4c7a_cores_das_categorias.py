"""cores das categorias

Revision ID: 5f5fce2a4c7a
Revises: af12b480e4ea
Create Date: 2026-11-22 21:21:41.744367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f5fce2a4c7a'
down_revision: Union[str, Sequence[str], None] = 'af12b480e4ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CEU = "#7dbde8"
PESSEGO = "#f0a27a"
LAVANDA = "#a996ee"
VERDE_AGUA = "#62c4b8"
AREIA = "#ddc170"
ROSA = "#ec93b8"

PASTEIS = [CEU, PESSEGO, LAVANDA, VERDE_AGUA, AREIA, ROSA]

CORES_PADRAO = {
    CEU: [
        "Aluguel", "Condomínio", "IPTU", "Água e Esgoto", "Energia Elétrica", "Gás",
        "Internet/TV", "Plano de Celular", "Manutenção e Reparos", "Móveis e Eletrodomésticos",
        "Serviços Domésticos", "Seguro Residencial",
        "Rendimentos de Investimentos", "Aluguéis Recebidos",
    ],
    PESSEGO: [
        "Supermercado/Feira", "Açougue e Peixaria", "Padaria e Cafeteria",
        "Restaurantes e Lanchonetes", "Delivery", "Refeição no Trabalho",
        "Freelance e Trabalhos Extras", "Vendas",
    ],
    LAVANDA: [
        "Cinema, Teatro e Shows", "Bares e Festas", "Passeios e Parques", "Viagens e Hospedagem",
        "Jogos e Hobbies", "Streaming de Música", "Streaming de Vídeo", "Nuvem e Softwares",
        "Eletrônicos e Informática", "Manutenção de Eletrônicos",
        "Bolsa e Auxílios", "Restituição do Imposto de Renda", "Reembolsos",
    ],
    VERDE_AGUA: [
        "Academia e Esportes", "Consultas e Exames", "Dentista", "Farmácia e Medicamentos",
        "Plano de Saúde/Odontológico", "Terapia e Psicologia", "Óptica", "Higiene Pessoal",
        "Cosméticos e Perfumaria", "Barbearia", "Salão", "Seguro de Vida",
        "Salário", "13º Salário", "Adicional de Férias",
    ],
    AREIA: [
        "Aplicativos de Corridas", "Combustível", "Estacionamento e Pedágio",
        "IPVA e Licenciamento", "Lava-jato", "Manutenção do Veículo", "Multas de Trânsito",
        "Seguro Auto/Moto", "Transporte Público",
        "Empréstimos e Financiamentos", "Imposto de Renda (IRPF)", "Juros e Multas",
        "Tarifas Bancárias", "Taxas e Documentos",
        "Outras Receitas",
    ],
    ROSA: [
        "Cuidados com Crianças", "Escola", "Faculdade", "Cursos Livres e Idiomas",
        "Plataformas de Ensino", "Material Escolar e Livros", "Mesada dos Filhos",
        "Pensão Alimentícia", "Banho e Tosa", "Ração e Petiscos", "Veterinário e Vacinas",
        "Roupas", "Calçados", "Acessórios", "Presentes e Doações", "Imprevistos",
        "Outras Despesas",
        "Presentes Recebidos",
    ],
}


def upgrade() -> None:
    atualizar = sa.text(
        "UPDATE categoria SET cor = :cor WHERE id_usuario IS NULL AND nome = ANY(:nomes)"
    )
    for cor, nomes in CORES_PADRAO.items():
        op.execute(atualizar.bindparams(cor=cor, nomes=nomes))

    op.execute(
        sa.text(
            """
            UPDATE categoria AS c
            SET cor = (:pasteis)[1 + (ordem.posicao - 1) % 6]
            FROM (
                SELECT id_categoria,
                       row_number() OVER (PARTITION BY id_usuario ORDER BY nome) AS posicao
                FROM categoria
                WHERE id_usuario IS NOT NULL
            ) AS ordem
            WHERE c.id_categoria = ordem.id_categoria
            """
        ).bindparams(sa.bindparam("pasteis", PASTEIS, type_=sa.ARRAY(sa.String())))
    )


def downgrade() -> None:
    pass
