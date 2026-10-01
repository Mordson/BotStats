"""
Game → genre mapping and per-genre aggregation.

Discord presence doesn't report a game's genre, so it's assigned here by hand.
Each game belongs to exactly one genre, so genre totals always add up to the
total playtime of every classified game.

Keys are lowercased, already-normalized activity names (see
`core.repositories._normalize_activity_name`) - i.e. exactly what
`ActivitySessionRepository.top_games` returns, lowercased.

Adding a new game: check `GET /stats/unclassified-games`, then add each listed
name either to `GAME_GENRES` or to `IGNORED_GAMES`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

UNCLASSIFIED = "Bez kategorii"

GAME_GENRES: dict[str, str] = {
    # MMO
    "world of tanks": "MMO",
    "war thunder": "MMO",
    # Strzelanki
    "fortnite": "Strzelanki",
    "retrac": "Strzelanki",  # Fortnite private server
    "s.t.a.l.k.e.r. 2 heart of chornobyl": "Strzelanki",
    "counter-strike 2": "Strzelanki",
    "ghost recon breakpoint": "Strzelanki",
    "tom clancy's ghost recon breakpoint": "Strzelanki",
    "arena breakout infinite": "Strzelanki",
    "call of duty black ops 7": "Strzelanki",
    "call of duty wwii": "Strzelanki",
    "battlefield 6": "Strzelanki",
    "delta force": "Strzelanki",
    "aim/flash trainer": "Strzelanki",
    # Survival
    "7 days to die": "Survival",
    "starrupture": "Survival",
    "satisfactory": "Survival",
    "no man's sky": "Survival",
    "minecraft": "Survival",
    "tlauncher": "Survival",  # Minecraft launcher
    "icarus": "Survival",
    "valheim": "Survival",
    # Symulatory
    "american truck simulator": "Symulatory",
    "thehunter call of the wild": "Symulatory",
    "forza horizon 6": "Symulatory",
    "assetto corsa competizione": "Symulatory",
    # RPG
    "kingdom come deliverance": "RPG",
    "kingdom come deliverance ii": "RPG",
    "assassin's creed valhalla": "RPG",
    # MOBA
    "league of legends": "MOBA",
    # Strategie
    "company of heroes": "Strategie",
    "warcraft iii reign of chaos": "Strategie",
    "colonist": "Strategie",
}

# Activities left out of genre stats entirely: Roblox (a platform, not a genre),
# non-game apps, and casual games. They still show up in the per-game stats.
IGNORED_GAMES: frozenset[str] = frozenset(
    {
        "roblox",
        "roblox with medal",
        "curseforge",
        "bongo cat",
        "stumble guys",
        "geometry dash",
        "wordle",
        "spelunky",
        "viewfinder",
        "timberman",
        "yet another zombie defense hd",
    }
)


@dataclass
class GenreTotal:
    genre: str
    total_seconds: int = 0
    top_games: list[tuple[str, int]] = field(default_factory=list)


def aggregate_by_genre(
    game_totals: list[tuple[str, int]], top_games_per_genre: int = 3
) -> list[GenreTotal]:
    """
    Groups per-game totals (name, seconds) into genres, sorted by time descending.

    Ignored games are dropped; games missing from the mapping are grouped under
    `UNCLASSIFIED`. Each genre keeps its `top_games_per_genre` most-played games.
    """
    genres: dict[str, GenreTotal] = {}
    for name, seconds in sorted(game_totals, key=lambda row: row[1], reverse=True):
        key = name.lower()
        if key in IGNORED_GAMES or seconds <= 0:
            continue
        genre = GAME_GENRES.get(key, UNCLASSIFIED)
        bucket = genres.setdefault(genre, GenreTotal(genre))
        bucket.total_seconds += seconds
        if len(bucket.top_games) < top_games_per_genre:
            bucket.top_games.append((name, seconds))
    return sorted(genres.values(), key=lambda g: g.total_seconds, reverse=True)


def unclassified_games(game_totals: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Games (name, seconds) that are neither mapped to a genre nor ignored, by time descending."""
    unmapped = [
        (name, seconds)
        for name, seconds in game_totals
        if name.lower() not in GAME_GENRES and name.lower() not in IGNORED_GAMES
    ]
    return sorted(unmapped, key=lambda row: row[1], reverse=True)
