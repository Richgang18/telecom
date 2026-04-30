"""
test_deploy.py — Unit tests for deploy.py orchestration.

Sub-task 15.1:
  - deploy.py calls each setup script in the correct order
  - setup_windows_host.ps1 is invoked after all WSL2 scripts complete
  - A failure in any setup script halts execution and logs the error

Requirements: 1.4, 13.1
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from deploy import (
    STEPS,
    DeploymentError,
    _run_step,
    main,
)


# ===========================================================================
# Tests for _run_step()
# ===========================================================================


class TestRunStep:
    """Unit tests for the _run_step() helper."""

    def test_run_step_calls_function(self) -> None:
        """_run_step must call the provided function exactly once."""
        mock_fn = MagicMock()
        _run_step("test step", mock_fn)
        mock_fn.assert_called_once_with()

    def test_run_step_raises_deployment_error_on_exception(self) -> None:
        """
        _run_step must raise DeploymentError when the function raises any
        exception.

        Requirements: 13.1
        """
        def failing_fn() -> None:
            raise RuntimeError("simulated failure")

        with pytest.raises(DeploymentError, match="simulated failure"):
            _run_step("failing step", failing_fn)

    def test_run_step_wraps_value_error(self) -> None:
        """_run_step must wrap ValueError in DeploymentError."""
        def bad_fn() -> None:
            raise ValueError("bad value")

        with pytest.raises(DeploymentError):
            _run_step("bad step", bad_fn)

    def test_run_step_wraps_os_error(self) -> None:
        """_run_step must wrap OSError in DeploymentError."""
        def io_fn() -> None:
            raise OSError("disk full")

        with pytest.raises(DeploymentError):
            _run_step("io step", io_fn)

    def test_run_step_does_not_raise_on_success(self) -> None:
        """_run_step must not raise when the function succeeds."""
        _run_step("ok step", lambda: None)  # Should not raise


# ===========================================================================
# Tests for main() — step ordering and failure halting
# ===========================================================================


class TestMainOrchestration:
    """
    Unit tests for the main() orchestration function.

    Requirements: 1.4, 13.1
    """

    def _make_steps(self, names: list[str]) -> list[tuple[str, MagicMock]]:
        """Build a list of (name, mock_fn) tuples."""
        return [(name, MagicMock()) for name in names]

    def test_main_calls_all_steps_in_order(self) -> None:
        """
        main() must call every step function in the order they appear in
        the steps list.

        Requirements: 1.4
        """
        call_order: list[str] = []

        def make_fn(name: str):
            def fn():
                call_order.append(name)
            return fn

        step_names = ["step_a", "step_b", "step_c", "step_d"]
        steps = [(name, make_fn(name)) for name in step_names]

        result = main(steps=steps)

        assert result == 0, f"main() returned {result}, expected 0"
        assert call_order == step_names, (
            f"Steps called in wrong order: {call_order}"
        )

    def test_main_halts_on_first_failure(self) -> None:
        """
        main() must halt execution when any step raises an exception and
        must not call subsequent steps.

        Requirements: 13.1
        """
        call_order: list[str] = []

        def ok_fn(name: str):
            def fn():
                call_order.append(name)
            return fn

        def fail_fn(name: str):
            def fn():
                call_order.append(name)
                raise RuntimeError(f"{name} failed")
            return fn

        steps = [
            ("step_1", ok_fn("step_1")),
            ("step_2", ok_fn("step_2")),
            ("step_3", fail_fn("step_3")),   # This step fails
            ("step_4", ok_fn("step_4")),     # Must NOT be called
            ("step_5", ok_fn("step_5")),     # Must NOT be called
        ]

        result = main(steps=steps)

        assert result == 1, f"main() returned {result}, expected 1 (failure)"
        assert "step_4" not in call_order, (
            "step_4 was called after step_3 failed — execution should have halted"
        )
        assert "step_5" not in call_order, (
            "step_5 was called after step_3 failed — execution should have halted"
        )
        assert call_order == ["step_1", "step_2", "step_3"], (
            f"Unexpected call order: {call_order}"
        )

    def test_main_returns_0_on_success(self) -> None:
        """main() must return 0 when all steps succeed."""
        steps = [("ok", lambda: None), ("ok2", lambda: None)]
        result = main(steps=steps)
        assert result == 0

    def test_main_returns_1_on_failure(self) -> None:
        """main() must return 1 when any step fails."""
        def fail():
            raise RuntimeError("fail")

        steps = [("fail", fail)]
        result = main(steps=steps)
        assert result == 1

    def test_main_empty_steps_returns_0(self) -> None:
        """main() with an empty steps list must return 0."""
        result = main(steps=[])
        assert result == 0


# ===========================================================================
# Tests for STEPS ordering — Windows host script comes after WSL2 scripts
# ===========================================================================


class TestStepsOrdering:
    """
    Tests verifying the STEPS list has the correct ordering.

    Requirements: 1.4
    """

    def _step_index(self, keyword: str) -> int:
        """Return the index of the first step whose name contains *keyword*."""
        for i, (name, _) in enumerate(STEPS):
            if keyword.lower() in name.lower():
                return i
        raise ValueError(f"No step found containing keyword {keyword!r}")

    def test_provision_is_first(self) -> None:
        """Provision step must be first."""
        assert self._step_index("provision") == 0, (
            "Provision step must be the first step"
        )

    def test_tls_comes_after_provision(self) -> None:
        """TLS step must come after provision."""
        assert self._step_index("tls") > self._step_index("provision"), (
            "TLS step must come after provision"
        )

    def test_firewall_comes_after_tls(self) -> None:
        """Firewall step must come after TLS."""
        assert self._step_index("firewall") > self._step_index("tls"), (
            "Firewall step must come after TLS"
        )

    def test_fail2ban_comes_after_firewall(self) -> None:
        """Fail2Ban step must come after firewall."""
        assert self._step_index("fail2ban") > self._step_index("firewall"), (
            "Fail2Ban step must come after firewall"
        )

    def test_pjsip_comes_after_fail2ban(self) -> None:
        """pjsip.conf generation must come after Fail2Ban."""
        assert self._step_index("pjsip") > self._step_index("fail2ban"), (
            "pjsip step must come after fail2ban"
        )

    def test_dialplan_comes_after_pjsip(self) -> None:
        """Dialplan generation must come after pjsip."""
        assert self._step_index("extensions") > self._step_index("pjsip"), (
            "Dialplan step must come after pjsip"
        )

    def test_cdr_comes_after_dialplan(self) -> None:
        """CDR step must come after dialplan."""
        assert self._step_index("cdr") > self._step_index("extensions"), (
            "CDR step must come after dialplan"
        )

    def test_ami_comes_after_cdr(self) -> None:
        """AMI step must come after CDR."""
        assert self._step_index("ami") > self._step_index("cdr"), (
            "AMI step must come after CDR"
        )

    def test_windows_host_comes_after_ami(self) -> None:
        """
        Windows host setup must come after all WSL2 scripts (after AMI).

        Requirements: 1.4
        """
        assert self._step_index("windows") > self._step_index("ami"), (
            "Windows host setup must come after all WSL2 scripts"
        )

    def test_asterisk_reload_comes_after_windows_host(self) -> None:
        """Asterisk reload must come after Windows host setup."""
        assert self._step_index("reload") > self._step_index("windows"), (
            "Asterisk reload must come after Windows host setup"
        )

    def test_tests_come_last(self) -> None:
        """Test suite must be the last step."""
        test_idx = self._step_index("test")
        assert test_idx == len(STEPS) - 1, (
            f"Test suite must be the last step (index {len(STEPS) - 1}), "
            f"got index {test_idx}"
        )

    def test_windows_host_comes_before_tests(self) -> None:
        """
        Windows host setup must come before the test suite.

        Requirements: 1.4
        """
        assert self._step_index("windows") < self._step_index("test"), (
            "Windows host setup must come before the test suite"
        )

    def test_total_step_count(self) -> None:
        """STEPS list must contain exactly 11 steps."""
        assert len(STEPS) == 11, (
            f"Expected 11 deployment steps, got {len(STEPS)}"
        )
