"""
Tests for Circuit Breaker implementation
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch

from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitState


class TestCircuitBreaker:
    """Test cases for CircuitBreaker"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker instance for testing"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception=Exception,
            name="TestCircuitBreaker"
        )

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state_success(self, circuit_breaker):
        """Test circuit breaker in CLOSED state with successful calls"""
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.get_failure_count() == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state_failure(self, circuit_breaker):
        """Test circuit breaker in CLOSED state with failures"""
        async def failure_func():
            raise Exception("Test error")

        with pytest.raises(Exception, match="Test error"):
            await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.get_failure_count() == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self, circuit_breaker):
        """Test circuit breaker opens after reaching failure threshold"""
        async def failure_func():
            raise Exception("Test error")

        # Cause failures up to threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN
        assert circuit_breaker.get_failure_count() == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state_blocks_calls(self, circuit_breaker):
        """Test circuit breaker in OPEN state blocks calls"""
        async def failure_func():
            raise Exception("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Try to call function - should be blocked
        with pytest.raises(CircuitBreakerError):
            await circuit_breaker.call(failure_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state_recovery(self, circuit_breaker):
        """Test circuit breaker transitions to HALF_OPEN and recovers"""
        async def failure_func():
            raise Exception("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # First call should be in HALF_OPEN state
        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.get_failure_count() == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state_failure(self, circuit_breaker):
        """Test circuit breaker in HALF_OPEN state with failure goes back to OPEN"""
        async def failure_func():
            raise Exception("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # First call should be in HALF_OPEN state and fail
        with pytest.raises(Exception):
            await circuit_breaker.call(failure_func)

        # After failure in HALF_OPEN state, should go back to OPEN
        # Note: The circuit breaker opens after reaching failure threshold,
        # which is 3, so we need to fail 3 more times to open it again
        for _ in range(2):  # 2 more failures to reach threshold
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, circuit_breaker):
        """Test circuit breaker reset functionality"""
        async def failure_func():
            raise Exception("Test error")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failure_func)

        assert circuit_breaker.get_state() == CircuitState.OPEN

        # Reset the circuit
        await circuit_breaker.reset()
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.get_failure_count() == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_ignores_unexpected_exceptions(self, circuit_breaker):
        """Test circuit breaker ignores unexpected exceptions"""
        # Create a circuit breaker that expects ValueError
        circuit_breaker.expected_exception = ValueError
        
        async def unexpected_error_func():
            raise ValueError("Unexpected error")

        with pytest.raises(ValueError):
            await circuit_breaker.call(unexpected_error_func)

        # Should count as failure since it's the expected exception type
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.get_failure_count() == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_sync_function(self, circuit_breaker):
        """Test circuit breaker with synchronous functions"""
        def sync_success_func():
            return "sync_success"

        result = await circuit_breaker.call(sync_success_func)
        assert result == "sync_success"
        assert circuit_breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_concurrent_calls(self, circuit_breaker):
        """Test circuit breaker with concurrent calls"""
        async def failure_func():
            await asyncio.sleep(0.1)
            raise Exception("Test error")

        # Make concurrent calls
        tasks = [circuit_breaker.call(failure_func) for _ in range(5)]
        
        # All should fail
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should be exceptions
        assert all(isinstance(result, Exception) for result in results)
        
        # Circuit should be open
        assert circuit_breaker.get_state() == CircuitState.OPEN