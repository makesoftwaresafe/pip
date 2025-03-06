import math
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Sequence

import pytest

from pip._vendor.resolvelib.resolvers import RequirementInformation

from pip._internal.req.constructors import install_req_from_req_string
from pip._internal.resolution.resolvelib.base import Candidate
from pip._internal.resolution.resolvelib.candidates import REQUIRES_PYTHON_IDENTIFIER
from pip._internal.resolution.resolvelib.factory import Factory
from pip._internal.resolution.resolvelib.provider import PipProvider
from pip._internal.resolution.resolvelib.requirements import (
    ExplicitRequirement,
    SpecifierRequirement,
)

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference

    from pip._internal.resolution.resolvelib.base import Candidate, Requirement

    PreferenceInformation = RequirementInformation[Requirement, Candidate]


class FakeCandidate(Candidate):
    """A minimal fake candidate for testing purposes."""

    def __init__(self, *args: object, **kwargs: object) -> None: ...


def build_req_info(
    name: str, parent: Optional[Candidate] = None
) -> "PreferenceInformation":
    install_requirement = install_req_from_req_string(name)

    requirement_information: PreferenceInformation = RequirementInformation(
        requirement=SpecifierRequirement(install_requirement),
        parent=parent,
    )

    return requirement_information


def build_explicit_req_info(
    url: str, parent: Optional[Candidate] = None
) -> "PreferenceInformation":
    """Build a direct requirement using a minimal FakeCandidate."""
    direct_requirement = ExplicitRequirement(FakeCandidate(url))
    return RequirementInformation(requirement=direct_requirement, parent=parent)


@pytest.mark.parametrize(
    "identifier, information, backtrack_causes, user_requested, expected",
    [
        # Test case for REQUIRES_PYTHON_IDENTIFIER
        (
            REQUIRES_PYTHON_IDENTIFIER,
            {REQUIRES_PYTHON_IDENTIFIER: [build_req_info("python")]},
            [],
            {},
            (False, True, True, True, math.inf, True, REQUIRES_PYTHON_IDENTIFIER),
        ),
        # Pinned package with "=="
        (
            "pinned-package",
            {"pinned-package": [build_req_info("pinned-package==1.0")]},
            [],
            {},
            (True, True, False, True, math.inf, False, "pinned-package"),
        ),
        # Star-specified package, i.e. with "*"
        (
            "star-specified-package",
            {"star-specified-package": [build_req_info("star-specified-package==1.*")]},
            [],
            {},
            (True, True, True, True, math.inf, False, "star-specified-package"),
        ),
        # Package that caused backtracking
        (
            "backtrack-package",
            {"backtrack-package": [build_req_info("backtrack-package")]},
            [build_req_info("backtrack-package")],
            {},
            (True, True, True, False, math.inf, True, "backtrack-package"),
        ),
        # Root package requested by user
        (
            "root-package",
            {"root-package": [build_req_info("root-package")]},
            [],
            {"root-package": 1},
            (True, True, True, True, 1, True, "root-package"),
        ),
        # Unfree package (with specifier operator)
        (
            "unfree-package",
            {"unfree-package": [build_req_info("unfree-package<1")]},
            [],
            {},
            (True, True, True, True, math.inf, False, "unfree-package"),
        ),
        # Free package (no operator)
        (
            "free-package",
            {"free-package": [build_req_info("free-package")]},
            [],
            {},
            (True, True, True, True, math.inf, True, "free-package"),
        ),
        # Test case for "direct" preference (explicit URL)
        (
            "direct-package",
            {"direct-package": [build_explicit_req_info("direct-package")]},
            [],
            {},
            (True, False, True, True, math.inf, True, "direct-package"),
        ),
    ],
)
def test_get_preference(
    identifier: str,
    information: Dict[str, Iterable["PreferenceInformation"]],
    backtrack_causes: Sequence["PreferenceInformation"],
    user_requested: Dict[str, int],
    expected: "Preference",
    factory: Factory,
) -> None:
    provider = PipProvider(
        factory=factory,
        constraints={},
        ignore_dependencies=False,
        upgrade_strategy="to-satisfy-only",
        user_requested=user_requested,
    )

    preference = provider.get_preference(
        identifier, {}, {}, information, backtrack_causes
    )

    assert preference == expected, f"Expected {expected}, got {preference}"
