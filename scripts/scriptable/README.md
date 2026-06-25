# Scriptable — Phone Ping Scripts

Two iOS Scriptable scripts for "pinging" another phone in the house. iOS
cannot send real ICMP pings from Scriptable, so each script takes a
different practical approach.

## 1. `ping-wifes-phone.js` — Is she on the wifi?

Fires a short-timeout HTTP request at her phone's local IP. An iPhone on
wifi refuses connections on closed ports, which proves it is alive on the
network; a timeout means nothing answered.

Setup:
1. On her phone: Settings > Wi-Fi > tap (i) next to the network, note the IP.
2. In the router, create a DHCP reservation for her phone so the IP is permanent.
3. Edit `CONFIG.ip` in the script.
4. In Scriptable, tap + and paste the script in. Run it, add it as a home
   screen widget, or call it from a Shortcut.

Result shows as an alert (in app) or a notification (from widget/Shortcut).

Caveat: an iPhone asleep for a long time may stop answering. Most reliable
when her phone was used recently or is charging.

## 2. `buzz-wifes-phone.js` — Make her phone buzz

In-house intercom. Sends a high-priority push via ntfy.sh (free, no
account). Works on the same wifi or anywhere.

Setup:
1. Her phone: install the "ntfy" app, subscribe to the topic name from the
   script, allow notifications.
2. Your phone: edit `CONFIG.topic` in the script to a long unguessable name
   (anyone who knows the topic can send to it), paste into Scriptable.
3. Run it — it prompts for a message, then buzzes her phone.

Tip: add either script to the home screen via a Scriptable widget or a
Shortcuts shortcut for one-tap use.

## 3. `worldcup-2026-bracket.js` — Fillable knockout bracket

A 2026 World Cup knockout tracker you fill in as results come in. The schedule
scaffold (match numbers, dates, kickoff times in ET, venues, and the who-plays-who
slots like `1A`, `2B`, `3rd`, `Winner of match 74`) is baked in; you supply reality.

Everything you type is saved to `wc2026-state.json` in Scriptable's local
documents, so it survives reruns.

How to use (all in-app, tap to edit):
1. Paste into Scriptable and run. You get a scrollable table: Groups A-L on top,
   then Round of 32 -> Round of 16 -> Quarter-finals -> Semi-finals ->
   Third place -> Final.
2. Tap a **group row** -> enter the four teams in final 1-4 order. Group winners
   (`1X`) and runners-up (`2X`) then auto-populate everywhere in the bracket.
3. Tap a match with a **`3rd ...` slot** -> type which third-placed team FIFA
   assigned there (decided once all groups finish).
4. Tap any match whose **both teams are known** -> pick who advances. The winner
   auto-flows into the next round ("Winner of match N"). Re-tap to change/clear.

Data accuracy: dates/times/venues/pairings were assembled from public schedules
while the group stage was still running. Anything not fully confirmed is marked
`v: 1` in the code and shows a `(check)` flag in the app — correct it directly in
the `SCHEDULE` block (one place, top of the file). Times are US Eastern.

Sources used to build the scaffold:
- [Wikipedia — 2026 FIFA World Cup knockout stage](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage)
- [FIFA — knockout stage match schedule/bracket](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/knockout-stage-match-schedule-bracket)
- [ESPN — 2026 World Cup match schedule](https://www.espn.com/soccer/story/_/id/48939282/2026-fifa-world-cup-fixtures-results-match-schedule-group-stage-knockout-rounds-bracket)
- [Sky Sports — World Cup 2026 bracket and knockout fixtures](https://www.skysports.com/football/news/11095/13556636/world-cup-2026-bracket-and-knockout-fixtures-whos-facing-who-in-the-last-32-and-route-to-final)
- [Olympics.com — Round of 32 full schedule](https://www.olympics.com/en/news/fifa-world-cup-2026-bracket-round-32-full-schedule-live-updates)
