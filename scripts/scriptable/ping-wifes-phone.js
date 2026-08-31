// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: green; icon-glyph: wifi;

// ping-wifes-phone.js
// Checks whether her iPhone is reachable on the same wifi.
//
// How it works: Scriptable cannot send a real ICMP ping, so this fires a
// short-timeout HTTP request at her phone's IP. iPhones on wifi actively
// refuse connections on closed ports ("could not connect"), which proves
// the phone is alive on the network. A timeout means no device answered.
//
// Setup:
// 1. In the router, give her phone a DHCP reservation so its IP never changes
//    (find current IP on her phone: Settings > Wi-Fi > tap the (i) next to the network).
// 2. Put that IP in CONFIG.ip below.
// 3. Run from the Scriptable app, a home screen widget, or a Shortcut.
//
// Caveat: a deeply asleep iPhone can stop answering after a while. It is
// reliable when the phone has been used recently or is charging.

const CONFIG = {
  label: "Wife's iPhone",
  ip: "192.168.1.50", // <-- change to her phone's reserved IP
  ports: [62078, 80, 443], // 62078 = iOS lockdown service, usually answers
  timeoutSeconds: 2,
  attempts: 3,
};

async function probe(ip, port, timeoutSeconds) {
  const req = new Request(`http://${ip}:${port}/`);
  req.timeoutInterval = timeoutSeconds;
  try {
    await req.load();
    return "reachable"; // got an actual HTTP response
  } catch (e) {
    const msg = String(e).toLowerCase();
    if (
      msg.includes("could not connect") ||
      msg.includes("connection refused") ||
      msg.includes("reset by peer")
    ) {
      return "reachable"; // device is up, port is just closed
    }
    if (msg.includes("not connected to the internet") || msg.includes("network connection was lost")) {
      return "no-network"; // this phone isn't on wifi
    }
    return "silent"; // timed out — nothing answered at that IP
  }
}

async function checkPhone() {
  for (let attempt = 1; attempt <= CONFIG.attempts; attempt++) {
    for (const port of CONFIG.ports) {
      const result = await probe(CONFIG.ip, port, CONFIG.timeoutSeconds);
      if (result === "reachable") return "online";
      if (result === "no-network") return "no-network";
    }
  }
  return "offline";
}

const result = await checkPhone();

let title;
let body;
if (result === "online") {
  title = `${CONFIG.label} is on the wifi`;
  body = `Answered at ${CONFIG.ip}. She's in the house (or at least her phone is).`;
} else if (result === "no-network") {
  title = "You're not on wifi";
  body = "This phone has no local network connection, so the check can't run.";
} else {
  title = `${CONFIG.label} is not responding`;
  body = `No reply from ${CONFIG.ip}. Phone may be asleep, off wifi, or the IP changed.`;
}

if (config.runsInApp) {
  const alert = new Alert();
  alert.title = title;
  alert.message = body;
  alert.addAction("OK");
  await alert.present();
} else {
  const n = new Notification();
  n.title = title;
  n.body = body;
  n.sound = result === "online" ? "default" : "failure";
  await n.schedule();
}

Script.complete();
