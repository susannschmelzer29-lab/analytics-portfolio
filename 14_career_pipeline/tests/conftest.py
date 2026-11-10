from pathlib import Path

import pytest
import yaml

from careerpipe.profile import load_profile

FIXTURES = Path(__file__).parent / "fixtures"
VOCABULARY = Path(__file__).parents[1] / "vocabulary" / "skills.yaml"


@pytest.fixture
def raw_profile():
    return yaml.safe_load((FIXTURES / "profile.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def profile():
    return load_profile(FIXTURES / "profile.yaml")


@pytest.fixture
def config():
    return yaml.safe_load((FIXTURES / "config.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def vocabulary():
    from careerpipe.grounding import load_vocabulary

    return load_vocabulary(VOCABULARY)
