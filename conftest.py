import pytest
from dotenv import load_dotenv, find_dotenv

dotenv_path = find_dotenv()
if not dotenv_path:
    pytest.skip(".env file not found. Skipping all tests.", allow_module_level=True)
else:
    load_dotenv(dotenv_path)
