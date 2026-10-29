"""Exceptions spécifiques au connecteur HAL."""


class HalError(Exception):
    """Exception de base pour les erreurs du connecteur HAL."""


class HalNotFoundError(HalError):
    """Publication ou ressource HAL introuvable (HTTP 404 ou 0 résultat)."""


class HalApiError(HalError):
    """Erreur liée à la réponse de l'API HAL Solr (HTTP 5xx, JSON invalide)."""


class HalRateLimitError(HalError):
    """Débit limite d'appels vers l'API HAL atteint (HTTP 429)."""
