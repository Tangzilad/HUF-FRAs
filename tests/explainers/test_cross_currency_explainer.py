from src.explainers.cross_currency import CrossCurrencyExplainer


def test_cross_currency_explainer_contains_requested_sections():
    text = CrossCurrencyExplainer().explain()

    assert "Domestic/foreign discounting" in text
    assert "Required market inputs" in text
    assert "Interpolation" in text
    assert "Cross-currency DV01 mapping" in text
    assert "residual USD exposure" in text
    assert "Liquidity gaps" in text
    assert "Stale quotes" in text
    assert "Tenor mismatch risk" in text


def test_cross_currency_explainer_mentions_loader_contract_expectations():
    text = CrossCurrencyExplainer().explain()

    assert "quote_type='forward'" in text
    assert "unit='points'" in text
    assert "stale threshold: 30 minutes" in text
