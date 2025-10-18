## Running the test suite

The project uses pytest with configuration in `pytest.ini` and `pyproject.toml`.

Basic commands:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# With coverage
pytest --cov=src --cov=config --cov-report=term-missing
```

### Notes on settings precedence

`config.settings.Settings` now prioritizes explicit constructor arguments over environment/YAML sources. This makes tests like creating `Settings(MEDIA_PROCESSING_ENABLED=False)` deterministic. Environment variables can still override YAML; see `config/settings.py` for details.

### Message grouping in tests

`MessageGroup` does not accept a `messages` constructor argument. To build a group in tests, instantiate and add messages:

```python
from src.processor.message_aggregator import MessageGroup

group = MessageGroup()
group.add_message({"message_id": 1, "date": 1234567890, "text": "Task", "chat_id": 123})
```

### Git HTTPS credentials

`GitOperations._configure_https_credentials()` is idempotent to avoid double `set_url` calls when invoked multiple times during tests or initialization.
