"""Static support defaults — no project imports (imported by the settings registry).

Kept dependency-free so `core.settings_registry` can reference the same literal
without pulling the whole support package graph into its import cycle.
"""

DEFAULT_TG_GREETING = "Здравствуйте! Опишите ваш вопрос одним сообщением — оператор ответит здесь."
