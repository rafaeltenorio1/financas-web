import base64
import binascii
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.enums import TipoTransacao
from models.transacao import Transacao
from models.usuario import Usuario
from schemas.importacao import (
    TAMANHO_MAXIMO_ARQUIVO,
    ImportacaoIn,
    ImportacaoOut,
    ItemPrevia,
    PreviaIn,
    PreviaOut,
)
from utils.auth import get_usuario_atual
from utils.categorias import validar_categoria
from utils.csrf import verificar_csrf, verificar_origem
from utils.extratos import ExtratoInvalido, decodificar, detectar_formato, ler_csv, ler_ofx

router = APIRouter(
    prefix="/importacoes",
    tags=["importacoes"],
    dependencies=[Depends(verificar_origem), Depends(verificar_csrf)],
)


def _erro(mensagem: str, colunas: list[str] | None = None) -> HTTPException:
    return HTTPException(status_code=422, detail={"mensagem": mensagem, "colunas": colunas})


def _ler_base64(texto: str) -> bytes:
    if texto.startswith("data:") and "," in texto:
        texto = texto.split(",", 1)[1]
    try:
        return base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError):
        raise _erro("Arquivo inválido.")


@router.post("/previa", response_model=PreviaOut)
async def previa_importacao(
    dados: PreviaIn,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    conteudo = _ler_base64(dados.arquivo_base64)
    if len(conteudo) > TAMANHO_MAXIMO_ARQUIVO:
        raise _erro("O arquivo passa de 2 MB.")

    texto = decodificar(conteudo)
    formato = detectar_formato(texto)
    try:
        if formato == "ofx":
            lancamentos = ler_ofx(texto, usuario.fuso)
        else:
            mapeamento = dados.mapeamento.model_dump() if dados.mapeamento else None
            lancamentos = ler_csv(texto, usuario.fuso, mapeamento)
    except ExtratoInvalido as erro:
        raise _erro(erro.mensagem, erro.colunas)

    existentes = set(
        await db.scalars(
            select(Transacao.id_externo).where(
                Transacao.id_usuario == usuario.id_usuario,
                Transacao.id_externo.in_([l.id_externo for l in lancamentos]),
            )
        )
    )

    itens = []
    for lancamento in lancamentos:
        valor = -lancamento.valor if dados.inverter_sinal else lancamento.valor
        itens.append(
            ItemPrevia(
                data_hora=lancamento.data_hora,
                valor=abs(valor),
                tipo=TipoTransacao.DESPESA if valor < 0 else TipoTransacao.RECEITA,
                nome=lancamento.descricao[:255],
                id_externo=lancamento.id_externo,
                duplicada=lancamento.id_externo in existentes,
            )
        )

    return PreviaOut(
        formato=formato,
        total=len(itens),
        duplicadas=sum(item.duplicada for item in itens),
        itens=itens,
    )


@router.post("", status_code=201, response_model=ImportacaoOut)
async def importar_transacoes(
    dados: ImportacaoIn,
    usuario: Usuario = Depends(get_usuario_atual),
    db: AsyncSession = Depends(get_db),
):
    for id_categoria in {item.id_categoria for item in dados.itens if item.id_categoria}:
        await validar_categoria(db, id_categoria, usuario)

    resultado = await db.execute(
        insert(Transacao)
        .values(
            [
                {
                    "id_transacao": uuid.uuid4(),
                    "id_usuario": usuario.id_usuario,
                    **item.model_dump(),
                }
                for item in dados.itens
            ]
        )
        .on_conflict_do_nothing(constraint="uq_transacao_usuario_id_externo")
        .returning(Transacao.id_transacao)
    )
    criadas = len(resultado.all())
    await db.commit()

    return ImportacaoOut(criadas=criadas, ignoradas=len(dados.itens) - criadas)
