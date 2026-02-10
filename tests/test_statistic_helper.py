"""Tests for statistic_helper module."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pyonwater
import pytest
from homeassistant.components.recorder.models import StatisticMetaData
from homeassistant.const import UnitOfVolume

from custom_components.eyeonwater.statistic_helper import (
    UnrecognizedUnitError,
    convert_statistic_data,
    filter_newer_data,
    get_ha_native_unit_of_measurement,
    get_last_imported_time,
    get_statistic_metadata,
    get_statistic_name,
    get_statistics_id,
    normalize_id,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def test_normalize_id() -> None:
    """Test ID normalization."""
    assert normalize_id("ABC-123_def") == "abc_123_def"
    assert normalize_id("test@meter#01") == "test_meter_01"
    assert normalize_id("UPPER_CASE") == "upper_case"
    assert normalize_id("123-456-789") == "123_456_789"


def test_get_statistic_name() -> None:
    """Test statistic name generation."""
    assert get_statistic_name("12345") == "water_meter 12345 statistic"
    assert get_statistic_name("ABC-DEF") == "water_meter abc_def statistic"


def test_get_statistics_id() -> None:
    """Test statistics ID generation."""
    assert get_statistics_id("12345") == "sensor.water_meter_12345_statistic"
    assert get_statistics_id("ABC-DEF") == "sensor.water_meter_abc_def_statistic"


def test_get_ha_native_unit_of_measurement() -> None:
    """Test unit conversion from pyonwater to HA."""
    assert (
        get_ha_native_unit_of_measurement(pyonwater.NativeUnits.GAL)
        == UnitOfVolume.GALLONS
    )
    assert (
        get_ha_native_unit_of_measurement(pyonwater.NativeUnits.CF)
        == UnitOfVolume.CUBIC_FEET
    )
    assert (
        get_ha_native_unit_of_measurement(pyonwater.NativeUnits.CM)
        == UnitOfVolume.CUBIC_METERS
    )


def test_get_ha_native_unit_of_measurement_invalid() -> None:
    """Test unit conversion with invalid unit."""
    with pytest.raises(UnrecognizedUnitError):
        # Create a mock enum value that's not in the map
        invalid_unit = MagicMock()
        invalid_unit.value = "INVALID"
        get_ha_native_unit_of_measurement(invalid_unit)


def test_get_statistic_metadata(mock_meter: pyonwater.Meter) -> None:
    """Test statistic metadata generation."""
    metadata = get_statistic_metadata(mock_meter)

    assert isinstance(metadata, StatisticMetaData)
    assert metadata.has_mean is False
    assert metadata.has_sum is True
    assert metadata.source == "recorder"
    assert metadata.statistic_id == "sensor.water_meter_12345678_statistic"
    assert metadata.name == "water_meter 12345678 statistic"
    assert metadata.unit_of_measurement == UnitOfVolume.GALLONS


def test_convert_statistic_data(mock_data_points: list[pyonwater.DataPoint]) -> None:
    """Test conversion of data points to statistic data."""
    statistic_data = convert_statistic_data(mock_data_points)

    assert len(statistic_data) == 10
    assert statistic_data[0]["start"] == datetime(2026, 2, 1, 0, 0, 0)
    assert statistic_data[0]["state"] == 100.0
    assert statistic_data[0]["sum"] == 100.0

    assert statistic_data[5]["start"] == datetime(2026, 2, 1, 5, 0, 0)
    assert statistic_data[5]["state"] == 150.0
    assert statistic_data[5]["sum"] == 150.0


def test_convert_statistic_data_monotonic(
    mock_data_points_non_monotonic: list[pyonwater.DataPoint],
) -> None:
    """Test that convert_statistic_data enforces monotonicity."""
    statistic_data = convert_statistic_data(mock_data_points_non_monotonic)

    # Verify values are now monotonically increasing
    assert statistic_data[0]["sum"] == 100.0
    assert statistic_data[1]["sum"] == 110.0
    assert statistic_data[2]["sum"] == 110.0  # Clamped, not 105.0
    assert statistic_data[3]["sum"] == 115.0
    assert statistic_data[4]["sum"] == 120.0

    # Verify monotonicity across all points
    for i in range(1, len(statistic_data)):
        assert statistic_data[i]["sum"] >= statistic_data[i - 1]["sum"]


def test_filter_newer_data(mock_data_points: list[pyonwater.DataPoint]) -> None:
    """Test filtering of data points after a timestamp."""
    cutoff = datetime(2026, 2, 1, 5, 0, 0)
    filtered = filter_newer_data(mock_data_points, cutoff)

    # Should only include points after hour 5
    assert len(filtered) == 4
    assert all(point.dt > cutoff for point in filtered)
    assert filtered[0].dt == datetime(2026, 2, 1, 6, 0, 0)
    assert filtered[-1].dt == datetime(2026, 2, 1, 9, 0, 0)


def test_filter_newer_data_none_cutoff(
    mock_data_points: list[pyonwater.DataPoint],
) -> None:
    """Test filtering with None cutoff returns all data."""
    filtered = filter_newer_data(mock_data_points, None)
    assert filtered == mock_data_points
    assert len(filtered) == 10


def test_filter_newer_data_empty_list() -> None:
    """Test filtering empty list."""
    filtered = filter_newer_data([], datetime(2026, 2, 1, 0, 0, 0))
    assert filtered == []


@pytest.mark.asyncio
async def test_get_last_imported_time_no_data(hass: HomeAssistant) -> None:
    """Test get_last_imported_time with no existing statistics."""
    with patch(
        "custom_components.eyeonwater.statistic_helper.get_last_statistics",
        return_value={},
    ):
        last_time = await get_last_imported_time(hass, "sensor.test_meter")
        assert last_time is None


@pytest.mark.asyncio
async def test_get_last_imported_time_with_data(hass: HomeAssistant) -> None:
    """Test get_last_imported_time with existing statistics."""
    test_time = datetime(2026, 2, 1, 12, 0, 0)
    mock_stats = {
        "sensor.test_meter": [
            {
                "start": test_time,
                "mean": None,
                "min": None,
                "max": None,
                "last_reset": None,
                "state": 100.0,
                "sum": 100.0,
            }
        ]
    }

    with patch(
        "custom_components.eyeonwater.statistic_helper.get_last_statistics",
        return_value=mock_stats,
    ):
        last_time = await get_last_imported_time(hass, "sensor.test_meter")
        assert last_time == test_time
