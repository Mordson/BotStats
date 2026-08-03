# Pomysły na rozwój

Lista pomysłów na ulepszenie bota/dashboardu, nieprzypisanych jeszcze do żadnego sprintu/wydania.

## 1. Prawdziwe avatary Discord w rankingu

`dashboard/components/RankingList.tsx` renderuje tylko literę z inicjału zamiast avatara.

- Dodać kolumnę `avatar_hash` do `User` (`core/models.py`).
- Zapisywać ją w `TrackingService.ensure_user()` (`core/services.py`) na podstawie `member.avatar`.
- Zwracać w `UserOut` (`api/schemas.py`) i budować URL do CDN Discorda
  (`https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png`) w dashboardzie.

## 2. Komendy slash w bocie

Bot dziś tylko pasywnie zbiera dane — `bot/main.py` nie rejestruje żadnych komend użytkownika.

- `/stats` — własne statystyki (czas głosowy, top gry) bez wychodzenia z Discorda.
- `/top` — szybki ranking wysyłany jako embed na kanał.
- Reużyć istniejące repozytoria (`core/repositories.py`), żeby nie duplikować logiki z API.

## 3. Auto-odświeżanie / widok "kto jest teraz online"

Dashboard wymaga ręcznego kliknięcia ⟳ (`Dashboard.tsx`, `handleRefresh`).

- `setInterval` na okresowy refetch danych aktywnej karty.
- Osobna karta/sekcja "aktywni teraz" na podstawie sesji bez `end_time` (otwarte `VoiceSession`/`ActivitySession`).

## 4. Wykres trendu w czasie

Obecnie tylko sumy za wybrany okres (donut + lista), brak rozbicia dzień po dniu.

- Nowy endpoint w `api/routers/stats.py`, agregujący `duration_seconds` po dniu (grupowanie po `start_time::date`).
- Wykres liniowy w dashboardzie dla wybranego zakresu czasu (obok istniejącego donuta).

## 5. Cotygodniowe podsumowanie na kanał Discord

Element grywalizacji — bot wysyła okresowy ranking bez potrzeby wchodzenia na dashboard.

- Zadanie cykliczne w bocie (np. `discord.ext.tasks.loop`) wysyłające embed z top userami/grami tygodnia.
- Reużyć `VoiceSessionRepository`/`ActivitySessionRepository` z parametrem `since` (tak jak API).
- Kanał docelowy i włącz/wyłącz — nowy ustawienie w `config.py`.
