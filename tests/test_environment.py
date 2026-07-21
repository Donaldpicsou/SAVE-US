"""Environment-loading configuration coverage."""

import unittest
from unittest.mock import patch

from app import create_app


class EnvironmentConfigurationTestCase(unittest.TestCase):
    def test_local_dotenv_is_loaded_without_overriding_host_variables(self) -> None:
        with patch("app.load_dotenv") as load_dotenv:
            app = create_app()

        self.assertFalse(app.config["TESTING"])
        load_dotenv.assert_called_once_with(override=False)

    def test_test_configuration_does_not_load_local_credentials(self) -> None:
        with patch("app.load_dotenv") as load_dotenv:
            app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})

        self.assertTrue(app.config["TESTING"])
        load_dotenv.assert_not_called()
