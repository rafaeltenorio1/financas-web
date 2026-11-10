"""categorias padrao completas

Revision ID: 85ba15b30ff1
Revises: 7ba1feda90ba
Create Date: 2026-11-10 02:57:30.157777

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85ba15b30ff1'
down_revision: Union[str, Sequence[str], None] = '7ba1feda90ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Cole TUDO isto logo abaixo da linha "depends_on" da migração gerada pelo Alembic.
# (Os imports no meio do arquivo funcionam; se quiser, mova-os para o topo depois.)
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert

R = "RECEITA"
D = "DESPESA"

CATEGORIAS = [
    # --- Receitas ---
    ("Salário", R),
    ("13º Salário", R),
    ("Adicional de Férias", R),
    ("Freelance e Trabalhos Extras", R),
    ("Rendimentos de Investimentos", R),
    ("Aluguéis Recebidos", R),
    ("Vendas", R),
    ("Reembolsos", R),
    ("Restituição do Imposto de Renda", R),
    ("Bolsa e Auxílios", R),
    ("Presentes Recebidos", R),
    ("Outras Receitas", R),
    # --- Moradia ---
    ("Aluguel", D),
    ("Condomínio", D),
    ("IPTU", D),
    ("Energia Elétrica", D),
    ("Água e Esgoto", D),
    ("Gás", D),
    ("Internet/TV", D),
    ("Manutenção e Reparos", D),
    ("Móveis e Eletrodomésticos", D),
    ("Seguro Residencial", D),
    ("Serviços Domésticos", D),
    # --- Alimentação ---
    ("Supermercado/Feira", D),
    ("Açougue e Peixaria", D),
    ("Restaurantes e Lanchonetes", D),
    ("Delivery", D),
    ("Padaria e Cafeteria", D),
    ("Refeição no Trabalho", D),
    # --- Transporte ---
    ("Combustível", D),
    ("Transporte Público", D),
    ("Aplicativos de Corridas", D),
    ("Manutenção do Veículo", D),
    ("IPVA e Licenciamento", D),
    ("Seguro Auto/Moto", D),
    ("Estacionamento e Pedágio", D),
    ("Lava-jato", D),
    ("Multas de Trânsito", D),
    # --- Saúde ---
    ("Plano de Saúde/Odontológico", D),
    ("Farmácia e Medicamentos", D),
    ("Consultas e Exames", D),
    ("Dentista", D),
    ("Óptica", D),
    ("Academia e Esportes", D),
    ("Terapia e Psicologia", D),
    # --- Educação ---
    ("Escola", D),
    ("Faculdade", D),
    ("Cursos Livres e Idiomas", D),
    ("Material Escolar e Livros", D),
    ("Plataformas de Ensino", D),
    # --- Tecnologia e assinaturas ---
    ("Plano de Celular", D),
    ("Streaming de Vídeo", D),
    ("Streaming de Música", D),
    ("Nuvem e Softwares", D),
    ("Eletrônicos e Informática", D),
    ("Manutenção de Eletrônicos", D),
    # --- Cuidados pessoais ---
    ("Salão", D),
    ("Barbearia", D),
    ("Higiene Pessoal", D),
    ("Cosméticos e Perfumaria", D),
    # --- Lazer ---
    ("Cinema, Teatro e Shows", D),
    ("Viagens e Hospedagem", D),
    ("Passeios e Parques", D),
    ("Jogos e Hobbies", D),
    ("Bares e Festas", D),
    # --- Pets ---
    ("Ração e Petiscos", D),
    ("Veterinário e Vacinas", D),
    ("Banho e Tosa", D),
    # --- Família ---
    ("Mesada dos Filhos", D),
    ("Cuidados com Crianças", D),
    ("Pensão Alimentícia", D),
    # --- Vestuário ---
    ("Roupas", D),
    ("Calçados", D),
    ("Acessórios", D),
    # --- Finanças e impostos ---
    ("Tarifas Bancárias", D),
    ("Empréstimos e Financiamentos", D),
    ("Imposto de Renda (IRPF)", D),
    ("Juros e Multas", D),
    ("Seguro de Vida", D),
    ("Taxas e Documentos", D),
    # --- Outros ---
    ("Presentes e Doações", D),
    ("Imprevistos", D),
    ("Outras Despesas", D),
]

categoria = sa.table(
    "categoria",
    sa.column("id_categoria", sa.Uuid),
    sa.column("id_usuario", sa.Uuid),
    sa.column("nome", sa.String),
    sa.column(
        "tipo_padrao",
        postgresql.ENUM("RECEITA", "DESPESA", name="tipotransacao", create_type=False),
    ),
)


def upgrade() -> None:
    linhas = [
        {"id_categoria": uuid.uuid4(), "nome": nome, "tipo_padrao": tipo}
        for nome, tipo in CATEGORIAS
    ]
    stmt = insert(categoria).values(linhas)
    # Se a categoria padrão já existe (ex.: do primeiro seed), só atualiza o tipo.
    stmt = stmt.on_conflict_do_update(
        constraint="uq_categoria_usuario_nome",
        set_={"tipo_padrao": stmt.excluded.tipo_padrao},
    )
    op.execute(stmt)


def downgrade() -> None:
    # Vazio de propósito: apagar categorias padrão faria as transações dos
    # usuários perderem a categoria (ON DELETE SET NULL).
    pass
