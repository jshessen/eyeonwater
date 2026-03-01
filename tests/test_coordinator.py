"""Tests for the EyeOnWater coordinator."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from pyonwater import EyeOnWaterAPIError, EyeOnWaterAuthError

from custom_components.eyeonwater.coordinator import EyeOnWaterData

from .conftest import FakeDataPoint, _make_hass


@pytest.fixture
def eow_data(mock_account, mock_client) -> EyeOnWaterData:
    """Build an EyeOnWaterData instance with mocked deps."""
    hass = _make_hass()
    with (
        patch(
            "custom_components.eyeonwater.coordinator.aiohttp_client.async_get_clientsession",
        ),
        patch(
            "custom_components.eyeonwater.coordinator.Client",
            return_value=mock_client,
        ),
    ):
        return EyeOnWaterData(hass, mock_account)


# ---------- setup ----------


@pytest.mark.asyncio
async def test_setup_fetches_meters(eow_data, mock_account) -> None:
    """setup() should populate the meters list."""
    await eow_data.setup()
    mock_account.fetch_meters.assert_awaited_once()
    assert len(eow_data.meters) == 1


# ---------- read_meters ----------


@pytest.mark.asyncio
async def test_read_meters_success(eow_data) -> None:
    """read_meters should call read_meter_info + read_historical_data."""
    await eow_data.setup()
    meters = await eow_data.read_meters(days_to_load=3)
    assert len(meters) == 1
    meter = meters[0]
    meter.read_meter_info.assert_awaited_once()
    meter.read_historical_data.assert_awaited()


@pytest.mark.asyncio
async def test_read_meters_api_error_raises_update_failed(eow_data) -> None:
    """API errors should be wrapped in UpdateFailed."""
    await eow_data.setup()
    eow_data.meters[0].read_meter_info.side_effect = EyeOnWaterAPIError("fail")

    with pytest.raises(UpdateFailed):
        await eow_data.read_meters()


@pytest.mark.asyncio
async def test_read_meters_auth_error_raises_update_failed(eow_data) -> None:
    """Auth errors should be wrapped in UpdateFailed."""
    await eow_data.setup()
    eow_data.meters[0].read_meter_info.side_effect = EyeOnWaterAuthError("denied")

    with pytest.raises(UpdateFailed):
        await eow_data.read_meters()


@pytest.mark.asyncio
async def test_read_meters_empty_response_retries_with_one_day(eow_data) -> None:
    """Empty-response API errors should retry with a 1-day window rather than failing."""
    await eow_data.setup()
    meter = eow_data.meters[0]
    # First call: simulate empty-response error; fallback call: succeeds
    meter.read_historical_data.side_effect = [
        EyeOnWaterAPIError("json_invalid: EOF while parsing"),
        [FakeDataPoint()],
    ]

    # Should NOT raise — empty response is handled gracefully
    meters = await eow_data.read_meters(days_to_load=30)
    assert len(meters) == 1
    # Expect two calls: original days_to_load=30, then retry with days_to_load=1
    assert meter.read_historical_data.await_count == 2
    assert meter.read_historical_data.await_args_list[1].kwargs["days_to_load"] == 1


@pytest.mark.asyncio
async def test_read_meters_reads_all_meters(eow_data) -> None:
    """read_meters fetches all data; statistics import is the sensor's responsibility."""
    await eow_data.setup()
    meters = await eow_data.read_meters(days_to_load=3)
    assert len(meters) == 1
    eow_data.meters[0].read_meter_info.assert_awaited_once()
    eow_data.meters[0].read_historical_data.assert_awaited_once()


# ---------- import_historical_data ----------


@pytest.mark.asyncio
async def test_import_historical_data(eow_data) -> None:
    """import_historical_data should read data and call centralized_import_statistics."""
    await eow_data.setup()

    with patch(
        "custom_components.eyeonwater.coordinator.centralized_import_statistics",
        new_callable=AsyncMock,
    ) as mock_import:
        await eow_data.import_historical_data(days=30)

    eow_data.meters[0].read_historical_data.assert_awaited()
    mock_import.assert_called_once()
