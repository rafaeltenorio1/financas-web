import enum


class TipoTransacao(enum.Enum):
    RECEITA = "receita"
    DESPESA = "despesa"


class TipoPagamento(enum.Enum):
    PIX = "pix"
    CARTAO_CREDITO = "cartao de credito"
    CARTAO_DEBITO = "cartao de debito"
    BOLETO = "boleto"
    DINHEIRO = "dinheiro"