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
    # FPS
    "fortnite": "FPS",
    "retrac": "FPS",  # Fortnite private server
    "s.t.a.l.k.e.r. 2 heart of chornobyl": "FPS",
    "counter-strike 2": "FPS",
    "ghost recon breakpoint": "FPS",
    "tom clancy's ghost recon breakpoint": "FPS",
    "arena breakout infinite": "FPS",
    "call of duty black ops 7": "FPS",
    "call of duty wwii": "FPS",
    "call of duty modern warfare": "FPS",
    "battlefield 6": "FPS",
    "delta force": "FPS",
    "aim/flash trainer": "FPS",
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
    "cities skylines": "Symulatory",
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


TOP_GAMES_PER_GENRE = 3


def genre_of(name: str) -> str | None:
    """The game's genre, `UNCLASSIFIED` if it isn't mapped, or None if it's ignored."""
    key = name.lower()
    if key in IGNORED_GAMES:
        return None
    return GAME_GENRES.get(key, UNCLASSIFIED)


def aggregate_by_genre(game_totals: list[tuple[str, int]]) -> list[GenreTotal]:
    """
    Groups per-game totals (name, seconds) into genres, sorted by time descending.

    Ignored games are dropped; games missing from the mapping are grouped under
    `UNCLASSIFIED`. Each genre keeps its `TOP_GAMES_PER_GENRE` most-played games.
    """
    genres: dict[str, GenreTotal] = {}
    for name, seconds in sorted(game_totals, key=lambda row: row[1], reverse=True):
        genre = genre_of(name)
        if genre is None:
            continue
        bucket = genres.setdefault(genre, GenreTotal(genre))
        bucket.total_seconds += seconds
        if len(bucket.top_games) < TOP_GAMES_PER_GENRE:
            bucket.top_games.append((name, seconds))
    return sorted(genres.values(), key=lambda g: g.total_seconds, reverse=True)


def unclassified_games(game_totals: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Games (name, seconds) that are neither mapped to a genre nor ignored, by time descending."""
    unmapped = [(name, seconds) for name, seconds in game_totals if genre_of(name) == UNCLASSIFIED]
    return sorted(unmapped, key=lambda row: row[1], reverse=True)
