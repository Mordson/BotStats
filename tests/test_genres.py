from datetime import datetime, timedelta, timezone

from core.game_genres import GAME_GENRES, IGNORED_GAMES
from core.repositories import UserRepository, _normalize_activity_name
from tests.factories import activity_session


async def _play(db_session, *games: tuple[str, int], activity_type: str = "playing") -> None:
    """Records one closed session of `seconds` per (activity_name, seconds) for user 1."""
    await UserRepository(db_session).get_or_create(1, "alice", "Alice", [])
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    for name, seconds in games:
        await activity_session(db_session, 1, name, now, seconds=seconds, activity_type=activity_type)
    await db_session.commit()


async def test_top_genres_sums_games_into_their_genre(api_client, db_session):
    await _play(db_session, ("Counter-Strike 2", 100), ("Fortnite", 50), ("League of Legends", 30))

    response = api_client.get("/stats/top-genres")

    assert response.status_code == 200
    assert response.json() == [
        {
            "genre": "FPS",
            "total_seconds": 150,
            "top_games": [
                {"activity_name": "Counter-Strike 2", "total_seconds": 100},
                {"activity_name": "Fortnite", "total_seconds": 50},
            ],
        },
        {
            "genre": "MOBA",
            "total_seconds": 30,
            "top_games": [{"activity_name": "League of Legends", "total_seconds": 30}],
        },
    ]


async def test_top_genres_skips_ignored_and_buckets_unknown_games(api_client, db_session):
    await _play(db_session, ("ROBLOX", 500), ("Brand New Game", 40), ("LEAGUE OF LEGENDS", 20))
    await _play(db_session, ("Spotify", 900), activity_type="listening")

    response = api_client.get("/stats/top-genres")

    assert response.status_code == 200
    assert [(g["genre"], g["total_seconds"]) for g in response.json()] == [
        ("Bez kategorii", 40),
        ("MOBA", 20),
    ]


async def test_unclassified_games_lists_only_unmapped_games_by_time(api_client, db_session):
    await _play(
        db_session, ("Brand New Game", 40), ("Another One", 90), ("ROBLOX", 500), ("Fortnite", 60)
    )

    response = api_client.get("/stats/unclassified-games")

    assert response.status_code == 200
    assert response.json() == [
        {"activity_name": "Another One", "total_seconds": 90},
        {"activity_name": "Brand New Game", "total_seconds": 40},
    ]


def test_mapping_keys_are_normalized_lowercase_names():
    # A key that isn't what _normalize_activity_name produces (lowercased) would never match.
    for key in [*GAME_GENRES, *IGNORED_GAMES]:
        assert key == _normalize_activity_name(key).lower(), key


def test_mapping_uses_only_the_agreed_genres():
    # Catches typos - a misspelled genre would silently become a separate Donut slice.
    assert set(GAME_GENRES.values()) == {
        "MMO", "FPS", "Survival", "Symulatory", "RPG", "MOBA", "Strategie"
    }


def test_no_game_is_both_mapped_and_ignored():
    assert not set(GAME_GENRES) & IGNORED_GAMES
