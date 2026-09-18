# Discord Activity Bot

Tracks how users spend time on a private Discord server — presence in voice channels,
game/streaming/listening activity, and voice engagement — and exposes it through a dashboard.

## Language

**User**:
A Discord member seen on the tracked guild. Identified by their Discord snowflake ID.

**Voice Session**:
One continuous interval of a User's presence in a single voice channel, from join to leave
(or channel switch). Says nothing about whether the user was speaking, muted, or deafened —
only that they were present in the channel.
_Avoid_: Call, voice time (voice time is the *sum* of Voice Sessions, not a session itself)

**Activity Session**:
One continuous interval of a User engaging in a single game, stream, or listening activity
(e.g. "Playing Valorant", "Listening to Spotify"), as reported by Discord's rich presence.
Custom statuses are excluded — they change too often to represent a stable activity.
_Avoid_: Presence (Presence is the raw Discord concept; Activity Session is our derived record)

**Duration**:
The `duration_seconds` of a closed session, computed once at the moment the session closes
(join→leave, or activity start→end). Never computed live — leaderboards just sum stored values.

**Role IDs**:
The snowflake IDs of the Discord roles a User currently holds, refreshed on nearly every
tracked event. Drives which users' game/activity data is visible on the dashboard
(`VISIBLE_ROLE_IDS`) — a visibility/privacy filter, not an access-control mechanism.

**Voice State**:
Discord's own snapshot of a member's connection to a voice channel: which channel (if any),
plus the `self_mute`/`self_deaf` (user-chosen) and `mute`/`deaf` (moderator-imposed) flags.
Delivered via `on_voice_state_update` — the same event `voice_tracker.py` already consumes for
channel join/leave. Not a stored concept of ours; it's Discord's, read fresh on every event.
Moderator-imposed `mute`/`deaf` are explicitly out of scope for tracking (see Voice State
Session) — they reflect a moderation action, not the user's own engagement.

**Voice State Session**:
One continuous interval during which one dimension of a User's self-chosen Voice State
(`self_mute` or `self_deaf`) held a value, while the user was connected to *some* voice channel.
Not tied to a specific channel — switching channels without changing mute/deafen state does not
end the session; only an actual toggle (or leaving voice entirely) does. Stored as a single
table with a `kind` discriminator (`unmuted` | `undeafened`), mirroring how Activity Session
already handles multiple concurrent kinds via `activity_type` — deliberately not two separate
tables, and deliberately no `channel_id` (this is a per-user behavior metric, not a per-channel
one).
_Avoid_: Listening Session (collides with Activity Session's existing `listening` activity type
for Spotify) — use **Undeafened** for the headphones dimension instead.

**Unmuted** / **Undeafened**:
The two tracked `kind`s of Voice State Session: `self_mute == False` and `self_deaf == False`
respectively. Based only on the user's own choice — moderator-imposed `mute`/`deaf` never
produce a Voice State Session (see Voice State).

**Engagement**:
The share (%) of a User's voice-channel time, within a given time range, spent Unmuted (or,
separately, Undeafened) — i.e. Unmuted/Undeafened Voice State Session duration divided by total
Voice Session duration over the same range. A ratio, not an absolute duration: deliberately
chosen so it measures behavior rather than mere presence, which "Czas głosowy" already covers.
Surfaced on the dashboard as its own tab, alongside "Czas głosowy" / "Top gry" / "Użytkownik",
under the same `VISIBLE_ROLE_IDS` visibility rules as the rest of the dashboard.
_Avoid_: Activity (Activity Session already means something else — games/streaming/Spotify);
"real activity" / "realna aktywność" (the original, too-vague framing for this whole feature —
explicitly does **not** mean actual audio/speaking detection (VAD), which would require the bot
to join each voice channel as a voice client and read the voice-gateway directly — a materially
different, far more invasive/expensive capability that is out of scope).
