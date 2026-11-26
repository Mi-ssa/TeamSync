"""Reglas del agradecimiento entre compañeros.

Basado en la investigación sobre gratitud expresada: lo que la hace valiosa es
nombrar lo que hizo la otra persona ("elogio al otro", Algoe et al., 2016), no
un "gracias" genérico. Por eso el mensaje debe decir algo más que "gracias".
"""

import re
import unicodedata

# Palabras que por sí solas no cuentan qué hizo la persona.
_RELLENO = {
    "gracias", "muchas", "mil", "muchisimas", "graciaas", "thanks", "thank", "you",
    "thx", "ty", "gracia", "de", "verdad", "en", "serio", "por", "todo", "eres", "lo", "maximo",
    "crack", "bien", "buen", "trabajo", "genial", "excelente", "super", "muy",
}
MINIMO_CARACTERES = 15
MINIMO_CONTENIDO = 12


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_acentos if not unicodedata.combining(c))


def motivo_mensaje_insuficiente(mensaje: str) -> str | None:
    """Devuelve por qué el mensaje no basta, o None si está bien."""
    limpio = mensaje.strip()
    if len(limpio) < MINIMO_CARACTERES:
        return "Cuéntale qué hizo y cómo te ayudó (al menos 15 caracteres)."
    palabras = re.findall(r"[a-zñ]+", _normalizar(limpio))
    contenido = "".join(p for p in palabras if p not in _RELLENO)
    if len(contenido) < MINIMO_CONTENIDO:
        return "Un «gracias» a secas se siente genérico: menciona algo concreto que hizo y cómo te ayudó."
    return None
