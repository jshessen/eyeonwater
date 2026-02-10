"""Tests for EyeOnWater integration setup."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.eyeonwater.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pyonwater_client: AsyncMock,
    mock_account: AsyncMock,
) -> None:
    """Test successful setup of config entry."""
    mock_config_entry.add_to_hass(hass)

    mock_pyonwater_client.get_account = AsyncMock(return_value=mock_account)
    mock_account.meters = []

    with patch(
        "custom_components.eyeonwater.pyonwater.Client",
        return_value=mock_pyonwater_client,
    ), patch(
        "custom_components.eyeonwater.async_setup_platforms",
        return_value=True,
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is True
    assert mock_config_entry.state == ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_setup_entry_auth_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pyonwater_client: AsyncMock,
) -> None:
    """Test setup with authentication failure."""
    mock_config_entry.add_to_hass(hass)

    mock_pyonwater_client.authenticate.side_effect = Exception("Auth failed")

    with patch(
        "custom_components.eyeonwater.pyonwater.Client",
        return_value=mock_pyonwater_client,
    ):
        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert result is False
    assert mock_config_entry.state == ConfigEntryState.SETUP_ERROR


@pytest.mark.asyncio
async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pyonwater_client: AsyncMock,
    mock_account: AsyncMock,
) -> None:
    """Test unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    mock_pyonwater_client.get_account = AsyncMock(return_value=mock_account)
    mock_account.meters = []

    with patch(
        "custom_components.eyeonwater.pyonwater.Client",
        return_value=mock_pyonwater_client,
    ), patch(
        "custom_components.eyeonwater.async_setup_platforms",
        return_value=True,
    ), patch(
        "custom_components.eyeonwater.async_unload_platforms",
        return_value=True,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)

    assert result is True
    assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
    assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_reload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_pyonwater_client: AsyncMock,
    mock_account: AsyncMock,
) -> None:
    """Test reloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    mock_pyonwater_client.get_account = AsyncMock(return_value=mock_account)
    mock_account.meters = []

    with patch(
        "custom_components.eyeonwater.pyonwater.Client",
        return_value=mock_pyonwater_client,
    ), patch(
        "custom_components.eyeonwater.async_setup_platforms",
        return_value=True,
    ), patch(
        "custom_components.eyeonwater.async_unload_platforms",
        return_value=True,
    ):
        # Setup
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        assert mock_config_entry.state == ConfigEntryState.LOADED

        # Reload
        result = await hass.config_entries.async_reload(mock_config_entry.entry_id)

        assert result is True
        assert mock_config_entry.state == ConfigEntryState.LOADED
