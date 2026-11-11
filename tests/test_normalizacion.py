from utils.normalizacion import limpiar_sku, extraer_secuencia_lote

def test_sku():
    assert limpiar_sku("000836") == "836"
    assert limpiar_sku("0000") == "0"
    assert limpiar_sku("ET8715947") == "ET8715947"

def test_lote():
    assert extraer_secuencia_lote("20260901-ABC-15") == 15
    assert extraer_secuencia_lote(None) is None
