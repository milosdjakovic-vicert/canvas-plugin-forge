"""Tests for campaign configuration service."""
import json

import pytest

from custom_reminders.services.config import (
    CACHE_KEY_CONFIG,
    CACHE_TTL,
    CampaignConfig,
    load_config,
    save_config,
)


def test_campaign_config_defaults():
    """Test CampaignConfig has expected defaults."""
    config = CampaignConfig()

    assert config.clinic_name == "Our Clinic"
    assert config.clinic_phone == ""
    assert config.confirmation_enabled is True
    assert config.reminders_enabled is True
    assert config.noshow_enabled is True
    assert config.cancellation_enabled is True
    assert config.reminder_intervals == [10080, 1440, 120]


def test_campaign_config_to_dict():
    """Test CampaignConfig serialization."""
    config = CampaignConfig(clinic_name="Test Clinic", clinic_phone="555-1234")
    data = config.to_dict()

    assert data["clinic_name"] == "Test Clinic"
    assert data["clinic_phone"] == "555-1234"
    assert "confirmation_enabled" in data
    assert "reminder_intervals" in data


def test_campaign_config_from_dict():
    """Test CampaignConfig deserialization."""
    data = {"clinic_name": "Test Clinic", "clinic_phone": "555-1234", "confirmation_enabled": False}
    config = CampaignConfig.from_dict(data)

    assert config.clinic_name == "Test Clinic"
    assert config.clinic_phone == "555-1234"
    assert config.confirmation_enabled is False


def test_load_config_default(mocker):
    """Test loading config returns defaults when cache is empty."""
    mock_cache = mocker.Mock()
    mock_cache.get.return_value = None
    mocker.patch("custom_reminders.services.config.get_cache", return_value=mock_cache)

    config = load_config()

    assert isinstance(config, CampaignConfig)
    assert config.clinic_name == "Our Clinic"
    mock_cache.get.assert_called_once_with(CACHE_KEY_CONFIG)


def test_load_config_from_cache(mocker):
    """Test loading config from cache."""
    mock_cache = mocker.Mock()
    cached_data = json.dumps({"clinic_name": "Cached Clinic", "clinic_phone": "555-9999"})
    mock_cache.get.return_value = cached_data
    mocker.patch("custom_reminders.services.config.get_cache", return_value=mock_cache)

    config = load_config()

    assert config.clinic_name == "Cached Clinic"
    assert config.clinic_phone == "555-9999"


def test_save_config(mocker):
    """Test saving config to cache."""
    mock_cache = mocker.Mock()
    mocker.patch("custom_reminders.services.config.get_cache", return_value=mock_cache)

    config = CampaignConfig(clinic_name="Save Test", clinic_phone="555-0000")
    save_config(config)

    mock_cache.set.assert_called_once()
    call_args = mock_cache.set.call_args
    assert call_args[0][0] == CACHE_KEY_CONFIG
    assert call_args[1]["timeout_seconds"] == CACHE_TTL

    # Verify saved data can be deserialized
    saved_json = call_args[0][1]
    saved_data = json.loads(saved_json)
    assert saved_data["clinic_name"] == "Save Test"
    assert saved_data["clinic_phone"] == "555-0000"
