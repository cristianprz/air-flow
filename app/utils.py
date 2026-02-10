"""Utilitários de data/hora com fuso horário do Brasil (America/Sao_Paulo)."""

from datetime import datetime, timezone, timedelta

# Fuso horário do Brasil (UTC-3)
BRT = timezone(timedelta(hours=-3))


def now_brt():
    """Retorna o datetime atual no fuso horário do Brasil."""
    return datetime.now(BRT).replace(tzinfo=None)
