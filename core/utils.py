from babel.numbers import format_currency

# Tasa de cambio fija (ejemplo: 1 USD = 4000 COP)
USD_EXCHANGE_RATE = 4000

def format_price(amount, currency="COP", locale="es_CO"):
    """Formatea el precio con símbolo de moneda"""
    try:
        return format_currency(amount, currency, locale=locale)
    except:
        # Fallback simple
        if currency == "COP":
            return f"${amount:,.0f}".replace(",", ".")
        else:  # USD
            return f"US${amount:,.2f}"

def convert_currency(amount, from_currency="COP", to_currency="COP"):
    """Conversión simple con tasa fija"""
    if from_currency == to_currency:
        return float(amount)
    
    # Solo soportamos COP ↔ USD
    if from_currency == "COP" and to_currency == "USD":
        return float(amount) / USD_EXCHANGE_RATE
    elif from_currency == "USD" and to_currency == "COP":
        return float(amount) * USD_EXCHANGE_RATE
    else:
        # Para cualquier otra combinación, devolver original
        return float(amount)
