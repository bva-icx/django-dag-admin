from django.apps import AppConfig

app_name = 'dag_admin_tests'
class TestConfig(AppConfig):
    name = app_name
    verbose_name = "Test Admin for DAGs"
