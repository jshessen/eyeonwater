"""Tests for EyeOnWater sensor entities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pyonwater
import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfVolume
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.eyeonwater.const import DOMAIN, WATER_METER_NAME
from custom_components.eyeonwater.sensor import EyeOnWaterUnifiedSensor

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


@pytest.fixture
def unified_sensor(
    mock_meter: pyonwater.Meter, mock_coordinator: DataUpdateCoordinator
) -> EyeOnWaterUnifiedSensor:
    """Create a unified sensor instance."""
    return EyeOnWaterUnifiedSensor(
        meter=mock_meter,
        coordinator=mock_coordinator,
        last_imported_time=None,
    )


def test_unified_sensor_initialization(
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_meter: pyonwater.Meter,
) -> None:
    """Test unified sensor initialization."""
    assert unified_sensor.meter == mock_meter
    assert unified_sensor._uuid == "test_meter_uuid_1234"
    assert unified_sensor._id == "12345678"
    assert unified_sensor.name == f"{WATER_METER_NAME} 12345678"
    assert unified_sensor.unique_id == "test_meter_uuid_1234"
    assert unified_sensor.device_class == SensorDeviceClass.WATER
    assert unified_sensor.state_class == SensorStateClass.TOTAL_INCREASING
    assert unified_sensor.native_unit_of_measurement == UnitOfVolume.GALLONS
    assert unified_sensor.suggested_display_precision == 0


def test_unified_sensor_device_info(
    unified_sensor: EyeOnWaterUnifiedSensor,
) -> None:
    """Test unified sensor device info."""
    device_info = unified_sensor.device_info

    assert isinstance(device_info, DeviceInfo)
    assert device_info["identifiers"] == {(DOMAIN, "test_meter_uuid_1234")}
    assert device_info["name"] == f"{WATER_METER_NAME} 12345678"


def test_unified_sensor_available_property(
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test available property."""
    # Initially not available
    assert unified_sensor.available is False

    # After coordinator update
    unified_sensor._handle_coordinator_update()
    assert unified_sensor.available is True

    # When coordinator fails
    mock_coordinator.last_update_success = False
    unified_sensor._handle_coordinator_update()
    assert unified_sensor.available is False


def test_unified_sensor_native_value(
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test native_value property."""
    # Initially None
    assert unified_sensor.native_value is None

    # After coordinator update with data
    unified_sensor._handle_coordinator_update()
    assert unified_sensor.native_value == 200.0


def test_unified_sensor_extra_state_attributes(
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test extra_state_attributes property."""
    unified_sensor._handle_coordinator_update()

    attributes = unified_sensor.extra_state_attributes
    assert attributes is not None
    assert "meter_id" in attributes
    assert attributes["meter_id"] == "12345678"
    assert "meter_uuid" in attributes
    assert attributes["meter_uuid"] == "test-meter-uuid-1234"


@pytest.mark.asyncio
async def test_unified_sensor_async_added_to_hass(
    hass: HomeAssistant,
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test async_added_to_hass registers coordinator listener."""
    with patch.object(
        mock_coordinator, "async_add_listener"
    ) as mock_add_listener, patch.object(
        unified_sensor, "async_get_last_state", return_value=None
    ):
        await unified_sensor.async_added_to_hass()
        mock_add_listener.assert_called_once()


@pytest.mark.asyncio
async def test_unified_sensor_async_will_remove_from_hass(
    unified_sensor: EyeOnWaterUnifiedSensor,
) -> None:
    """Test async_will_remove_from_hass unsubscribes listener."""
    # Mock the unsubscribe callable
    unified_sensor._unsubscribe_coordinator = MagicMock()

    await unified_sensor.async_will_remove_from_hass()
    unified_sensor._unsubscribe_coordinator.assert_called_once()


@pytest.mark.asyncio
async def test_unified_sensor_restore_state(
    hass: HomeAssistant,
    unified_sensor: EyeOnWaterUnifiedSensor,
) -> None:
    """Test state restoration from recorder."""
    mock_state = MagicMock()
    mock_state.state = "150.5"
    mock_state.attributes = {"meter_id": "12345678"}

    with patch.object(
        unified_sensor, "async_get_last_state", return_value=mock_state
    ), patch.object(unified_sensor.coordinator, "async_add_listener"):
        await unified_sensor.async_added_to_hass()
        # State should be restored but not override coordinator data


@pytest.mark.asyncio
async def test_unified_sensor_import_historical_data(
    hass: HomeAssistant,
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_data_points: list[pyonwater.DataPoint],
) -> None:
    """Test historical data import."""
    unified_sensor.meter.get_historical_data = AsyncMock(
        return_value=mock_data_points
    )

    with patch(
        "custom_components.eyeonwater.sensor.async_import_statistics"
    ) as mock_import, patch(
        "custom_components.eyeonwater.sensor.get_last_imported_time",
        return_value=None,
    ):
        await unified_sensor._import_historical_data()

        # Verify statistics were imported
        mock_import.assert_called_once()
        call_args = mock_import.call_args
        assert call_args[0][0] == hass
        assert "metadata" in call_args[1]
        assert "stats" in call_args[1]


@pytest.mark.asyncio
async def test_unified_sensor_import_historical_data_no_data(
    hass: HomeAssistant,
    unified_sensor: EyeOnWaterUnifiedSensor,
) -> None:
    """Test historical data import with no data."""
    unified_sensor.meter.get_historical_data = AsyncMock(return_value=[])

    with patch(
        "custom_components.eyeonwater.sensor.async_import_statistics"
    ) as mock_import:
        await unified_sensor._import_historical_data()

        # Should not import empty data
        mock_import.assert_not_called()


def test_unified_sensor_handle_coordinator_update_no_data(
    unified_sensor: EyeOnWaterUnifiedSensor,
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test coordinator update with no data."""
    mock_coordinator.data = None
    unified_sensor._handle_coordinator_update()

    assert unified_sensor.available is False
    assert unified_sensor.native_value is None


def test_unified_sensor_unit_conversion_cubic_feet(
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test sensor with cubic feet unit."""
    meter = MagicMock(spec=pyonwater.Meter)
    meter.meter_uuid = "test-uuid"
    meter.meter_id = "12345"
    meter.native_unit_of_measurement = "CF"
    meter.native_unit = pyonwater.NativeUnits.CF
    meter.meter_info = MagicMock()
    meter.meter_info.sensors = MagicMock()
    meter.meter_info.sensors.endpoint_temperature = None

    sensor = EyeOnWaterUnifiedSensor(
        meter=meter,
        coordinator=mock_coordinator,
        last_imported_time=None,
    )

    assert sensor.native_unit_of_measurement == UnitOfVolume.CUBIC_FEET


def test_unified_sensor_unit_conversion_cubic_meters(
    mock_coordinator: DataUpdateCoordinator,
) -> None:
    """Test sensor with cubic meters unit."""
    meter = MagicMock(spec=pyonwater.Meter)
    meter.meter_uuid = "test-uuid"
    meter.meter_id = "12345"
    meter.native_unit_of_measurement = "CM"
    meter.native_unit = pyonwater.NativeUnits.CM
    meter.meter_info = MagicMock()
    meter.meter_info.sensors = MagicMock()
    meter.meter_info.sensors.endpoint_temperature = None

    sensor = EyeOnWaterUnifiedSensor(
        meter=meter,
        coordinator=mock_coordinator,
        last_imported_time=None,
    )

    assert sensor.native_unit_of_measurement == UnitOfVolume.CUBIC_METERS
