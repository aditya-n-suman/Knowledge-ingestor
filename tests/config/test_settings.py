from pathlib import Path

from knowledge_ingestor.config import Config


def test_defaults_when_no_file(tmp_path):
    config = Config.load(tmp_path / "missing.yaml")

    assert config.concurrency == 8
    assert config.timeout == 30.0
    assert config.max_retries == 3


def test_loads_overrides_from_yaml(tmp_path):
    path = tmp_path / "knowledge.yaml"
    path.write_text(
        "concurrency: 4\ntimeout: 10\ncache_dir: my-cache\nplugins:\n  github: false\n"
    )

    config = Config.load(path)

    assert config.concurrency == 4
    assert config.timeout == 10
    assert config.cache_dir == Path("my-cache")
    assert config.plugins == {"github": False}
