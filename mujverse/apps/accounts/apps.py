from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mujverse.apps.accounts"
    verbose_name = "Accounts & Profiles"

    def ready(self):
        import mujverse.apps.accounts.signals  # noqa
