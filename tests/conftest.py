"""Fixtures for EyeOnWater tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pyonwater
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eyeonwater.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Enable custom integrations for testing."""
    return enable_custom_integrations


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test@example.com",
            "password": "test_password",  # noqa: S106
        },
        entry_id="test_entry_id",
        title="EyeOnWater",
    )


@pytest.fixture
def mock_meter() -> pyonwater.Meter:
    """Create a mock meter."""
    meter = MagicMock(spec=pyonwater.Meter)
    meter.meter_uuid = "test-meter-uuid-1234"
    meter.meter_id = "12345678"
    meter.native_unit_of_measurement = "GAL"
    meter.native_unit = pyonwater.NativeUnits.GAL
    meter.meter_info = MagicMock()
    meter.meter_info.sensors = MagicMock()
    meter.meter_info.sensors.endpoint_temperature = None
    return meter


@pytest.fixture
def mock_data_points() -> list[pyonwater.DataPoint]:
    """Create mock data points."""
    base_time = datetime(2026, 2, 1, 0, 0, 0)
    return [
        pyonwater.DataPoint(
            dt=base_time + timedelta(hours=i),
            reading=100.0 + (i * 10.0),
            unit="GAL",
        )
        for i in range(10)
    ]


@pytest.fixture
def mock_data_points_non_monotonic() -> list[pyonwater.DataPoint]:
    """Create mock data points with non-monotonic values."""
    base_time = datetime(2026, 2, 1, 0, 0, 0)
    return [
        pyonwater.DataPoint(dt=base_time, reading=100.0, unit="GAL"),
        pyonwater.DataPoint(
            dt=base_time + timedelta(hours=1), reading=110.0, unit="GAL"
        ),
        pyonwater.DataPoint(
            dt=base_time + timedelta(hours=2), reading=105.0, unit="GAL"
        ),  # Decrease
        pyonwater.DataPoint(
            dt=base_time + timedelta(hours=3), reading=115.0, unit="GAL"
        ),
        pyonwater.DataPoint(
            dt=base_time + timedelta(hours=4), reading=120.0, unit="GAL"
        ),
    ]


@pytest.fixture
def mock_coordinator(
    hass: HomeAssistant, mock_meter: pyonwater.Meter
) -> DataUpdateCoordinator:
    """Create a mock coordinator."""
    coordinator = DataUpdateCoordinator(
        hass,
        None,  # type: ignore[arg-type]
        name="EyeOnWater",
        update_interval=timedelta(minutes=30),
    )
    coordinator.data = {
        "meter": mock_meter,
        "reading": pyonwater.DataPoint(
            dt=datetime(2026, 2, 10, 12, 0, 0), reading=200.0, unit="GAL"
        ),
    }
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
async def mock_pyonwater_client() -> AsyncMock:
    """Create a mock pyonwater client."""
    client = AsyncMock(spec=pyonwater.Client)
    client.authenticate = AsyncMock(return_value=True)
    client.get_account = AsyncMock()
    return client


@pytest.fixture
def mock_account() -> pyonwater.Account:
    """Create a mock account."""
    account = MagicMock(spec=pyonwater.Account)
    account.meters = []
    return account
