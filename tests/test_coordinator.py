"""Tests for EyeOnWater coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pyonwater
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.eyeonwater.coordinator import EyeOnWaterCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.fixture
def coordinator(
    hass: HomeAssistant,
    mock_pyonwater_client: AsyncMock,
    mock_account: pyonwater.Account,
) -> EyeOnWaterCoordinator:
    """Create a coordinator instance."""
    return EyeOnWaterCoordinator(
        hass=hass,
        client=mock_pyonwater_client,
        account=mock_account,
        update_interval=timedelta(minutes=30),
    )


@pytest.mark.asyncio
async def test_coordinator_update_success(
    coordinator: EyeOnWaterCoordinator,
    mock_account: pyonwater.Account,
    mock_meter: pyonwater.Meter,
    mock_data_points: list[pyonwater.DataPoint],
) -> None:
    """Test successful coordinator update."""
    mock_account.meters = [mock_meter]
    mock_meter.read = AsyncMock(return_value=mock_data_points[-1])

    data = await coordinator._async_update_data()

    assert data is not None
    assert len(data) == 1
    assert "meter" in data[0]
    assert "reading" in data[0]
    assert data[0]["meter"] == mock_meter
    assert data[0]["reading"] == mock_data_points[-1]


@pytest.mark.asyncio
async def test_coordinator_update_authentication_error(
    coordinator: EyeOnWaterCoordinator,
    mock_account: pyonwater.Account,
    mock_meter: pyonwater.Meter,
) -> None:
    """Test coordinator update with authentication error."""
    mock_account.meters = [mock_meter]
    mock_meter.read = AsyncMock(
        side_effect=pyonwater.exceptions.AuthenticationError("Invalid token")
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_request_error(
    coordinator: EyeOnWaterCoordinator,
    mock_account: pyonwater.Account,
    mock_meter: pyonwater.Meter,
) -> None:
    """Test coordinator update with request error."""
    mock_account.meters = [mock_meter]
    mock_meter.read = AsyncMock(
        side_effect=pyonwater.exceptions.RequestError("Connection timeout")
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_no_meters(
    coordinator: EyeOnWaterCoordinator,
    mock_account: pyonwater.Account,
) -> None:
    """Test coordinator update with no meters."""
    mock_account.meters = []

    data = await coordinator._async_update_data()

    assert data == []


@pytest.mark.asyncio
async def test_coordinator_update_multiple_meters(
    coordinator: EyeOnWaterCoordinator,
    mock_account: pyonwater.Account,
    mock_data_points: list[pyonwater.DataPoint],
) -> None:
    """Test coordinator update with multiple meters."""
    meter1 = AsyncMock(spec=pyonwater.Meter)
    meter1.meter_id = "meter1"
    meter1.read = AsyncMock(return_value=mock_data_points[0])

    meter2 = AsyncMock(spec=pyonwater.Meter)
    meter2.meter_id = "meter2"
    meter2.read = AsyncMock(return_value=mock_data_points[1])

    mock_account.meters = [meter1, meter2]

    data = await coordinator._async_update_data()

    assert len(data) == 2
    assert data[0]["meter"] == meter1
    assert data[0]["reading"] == mock_data_points[0]
    assert data[1]["meter"] == meter2
    assert data[1]["reading"] == mock_data_points[1]


@pytest.mark.asyncio
async def test_coordinator_update_partial_failure(
    coordinator: EyeOnWaterCoordinator,
    mock_account: pyonwater.Account,
    mock_data_points: list[pyonwater.DataPoint],
) -> None:
    """Test coordinator update with one meter failing."""
    meter1 = AsyncMock(spec=pyonwater.Meter)
    meter1.meter_id = "meter1"
    meter1.read = AsyncMock(return_value=mock_data_points[0])

    meter2 = AsyncMock(spec=pyonwater.Meter)
    meter2.meter_id = "meter2"
    meter2.read = AsyncMock(
        side_effect=pyonwater.exceptions.RequestError("Meter offline")
    )

    mock_account.meters = [meter1, meter2]

    # Should still return data for successful meter
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
