"""Tests for EyeOnWater config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pyonwater
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.eyeonwater.const import DOMAIN, USE_SINGLE_SENSOR_MODE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_form_user_flow(
    hass: HomeAssistant, mock_pyonwater_client: AsyncMock
) -> None:
    """Test user initiated config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(
        "custom_components.eyeonwater.config_flow.pyonwater.Client",
        return_value=mock_pyonwater_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",  # noqa: S106
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test_password",  # noqa: S106
    }


@pytest.mark.asyncio
async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test invalid authentication during config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_client = AsyncMock()
    mock_client.authenticate.side_effect = pyonwater.exceptions.AuthenticationError(
        "Invalid credentials"
    )

    with patch(
        "custom_components.eyeonwater.config_flow.pyonwater.Client",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "wrong_password",  # noqa: S106
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.asyncio
async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test connection error during config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_client = AsyncMock()
    mock_client.authenticate.side_effect = pyonwater.exceptions.RequestError(
        "Connection failed"
    )

    with patch(
        "custom_components.eyeonwater.config_flow.pyonwater.Client",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",  # noqa: S106
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_form_unknown_error(hass: HomeAssistant) -> None:
    """Test unknown error during config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_client = AsyncMock()
    mock_client.authenticate.side_effect = Exception("Unexpected error")

    with patch(
        "custom_components.eyeonwater.config_flow.pyonwater.Client",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",  # noqa: S106
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


@pytest.mark.asyncio
async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: config_entries.ConfigEntry
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={USE_SINGLE_SENSOR_MODE: True},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {USE_SINGLE_SENSOR_MODE: True}


@pytest.mark.asyncio
async def test_options_flow_default_values(
    hass: HomeAssistant, mock_config_entry: config_entries.ConfigEntry
) -> None:
    """Test options flow with default values."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id
    )

    # Default should be False for single sensor mode
    assert result["data_schema"].schema.get(USE_SINGLE_SENSOR_MODE) is not None


@pytest.mark.asyncio
async def test_duplicate_entry(
    hass: HomeAssistant,
    mock_config_entry: config_entries.ConfigEntry,
    mock_pyonwater_client: AsyncMock,
) -> None:
    """Test duplicate config entry."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.eyeonwater.config_flow.pyonwater.Client",
        return_value=mock_pyonwater_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",  # Same as existing entry
                CONF_PASSWORD: "test_password",  # noqa: S106
            },
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
