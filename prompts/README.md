# Prompts versionnés

Ce répertoire contient les versions tracées des prompts utilisés par le pipeline (`csc.llm`).

Chaque modification d'un prompt doit :
1. Incrémenter la version du prompt.
2. Être référencée dans les appels LLM pour traçabilité intégrale (`prompt_id`, `prompt_version`, `prompt_sha`).
