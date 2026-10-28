"""Exceptions spécifiques au connecteur OpenAlex."""


class OpenAlexError(Exception):
    """Exception de base pour les erreurs OpenAlex."""


class OpenAlexRateLimitError(OpenAlexError):
    """Erreur levée lors d'un dépassement de débit HTTP 429 persistant."""


class OpenAlexBudgetExceededError(OpenAlexError):
    """Erreur levée lorsque le seuil du budget journalier gratuit (90%) est atteint."""


class OpenAlexNotFoundError(OpenAlexError):
    """Erreur levée lorsqu'une entité ou ressource n'est pas trouvée (HTTP 404)."""


class OpenAlexApiError(OpenAlexError):
    """Erreur levée en cas d'erreur de communication ou réponse inattendue de l'API."""
