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
