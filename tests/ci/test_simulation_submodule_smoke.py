from __future__ import annotations


def test_simulation_cli_wrapper_imports() -> None:
    # Import should remain side-effect-light; wrapper selects larrak_simulation when installed.
    from larrak2.cli import validate_simulation_main

    assert callable(validate_simulation_main)
