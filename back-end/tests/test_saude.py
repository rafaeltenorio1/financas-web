async def test_saude_confere_api_e_banco(client):
    resposta = await client.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"api": "ok", "banco": True}
