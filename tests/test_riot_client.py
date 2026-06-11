"""Tests for the Riot client. All HTTP is mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from analyser.riot_client import (
    PLATFORM_TO_REGION,
    RiotAPIError,
    RiotClient,
    RiotConfig,
)


@pytest.fixture
def client():
    return RiotClient(RiotConfig(api_key="fake-key", platform="euw1", region="europe"))


def test_platform_region_mapping_covers_known_platforms():
    for platform in ("na1", "euw1", "kr", "br1", "oc1"):
        assert platform in PLATFORM_TO_REGION


def test_api_key_header_sent(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"puuid": "x"}
    with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
        client.account_by_riot_id("Test", "EUW")
    assert client._session.headers.get("X-Riot-Token") == "fake-key"
    mock_get.assert_called_once()


def test_account_by_riot_id_builds_correct_url(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"puuid": "abc"}
    with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
        client.account_by_riot_id("Faker", "KR1")
    called_url = mock_get.call_args[0][0]
    assert "europe.api.riotgames.com" in called_url
    assert "/riot/account/v1/accounts/by-riot-id/Faker/KR1" in called_url


def test_match_ids_passes_queue_filter(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = ["m1", "m2"]
    with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
        client.match_ids_by_puuid("p", count=5, queue=420)
    params = mock_get.call_args.kwargs["params"]
    assert params["queue"] == 420
    assert params["count"] == 5


def test_404_raises_riot_api_error(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not found"
    with patch.object(client._session, "get", return_value=mock_resp):
        with pytest.raises(RiotAPIError, match="Not found"):
            client.account_by_riot_id("Ghost", "X")


def test_rate_limit_retries_after_sleep(client):
    rate_limited = MagicMock(status_code=429, headers={"Retry-After": "0"})
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"puuid": "p"}

    with patch.object(client._session, "get", side_effect=[rate_limited, ok]):
        with patch("analyser.riot_client.time.sleep"):
            result = client.account_by_riot_id("Test", "EUW")
    assert result == {"puuid": "p"}


def test_config_from_env_requires_api_key(monkeypatch):
    monkeypatch.delenv("RIOT_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="RIOT_API_KEY"):
        RiotConfig.from_env()


def test_config_from_env_routes_platform_to_region(monkeypatch):
    monkeypatch.setenv("RIOT_API_KEY", "fake")
    cfg_kr = RiotConfig.from_env(platform="kr")
    assert cfg_kr.region == "asia"
    cfg_na = RiotConfig.from_env(platform="na1")
    assert cfg_na.region == "americas"
