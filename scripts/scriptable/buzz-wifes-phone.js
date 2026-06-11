// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: orange; icon-glyph: bell;

// buzz-wifes-phone.js
// Actually pings her phone — sends a push notification that buzzes it,
// like an in-house intercom. Works over wifi or anywhere.
//
// Uses ntfy.sh (free, no account needed).
//
// Her setup (one time):
// 1. Install the "ntfy" app from the App Store on her phone.
// 2. In ntfy, subscribe to the exact topic name in CONFIG.topic below.
// 3. Allow notifications for the ntfy app.
//
// Your setup:
// 1. Change CONFIG.topic to something long and unguessable — anyone who
//    knows the topic name can send to it.
// 2. Run this script from Scriptable, a widget, or a Shortcut.

const CONFIG = {
  topic: "naturesseed-home-ping-CHANGE-ME-x7k3q9", // <-- make this unique
  senderName: "Gabe",
  defaultMessage: "Ping! Where are you?",
  askForMessage: true, // when run in-app, lets you type a custom message
};

async function main() {
  let message = CONFIG.defaultMessage;

  if (CONFIG.askForMessage && config.runsInApp) {
    const prompt = new Alert();
    prompt.title = "Ping wife's phone";
    prompt.addTextField("Message", CONFIG.defaultMessage);
    prompt.addAction("Send");
    prompt.addCancelAction("Cancel");
    const choice = await prompt.presentAlert();
    if (choice === -1) return; // cancelled
    message = prompt.textFieldValue(0) || CONFIG.defaultMessage;
  }

  const req = new Request(`https://ntfy.sh/${encodeURIComponent(CONFIG.topic)}`);
  req.method = "POST";
  req.headers = {
    Title: CONFIG.senderName,
    Priority: "high", // high priority = vibrates even in some focus modes
    Tags: "bell",
  };
  req.body = message;

  try {
    await req.loadString();
    if (config.runsInApp) {
      const ok = new Alert();
      ok.title = "Sent";
      ok.message = `"${message}"`;
      ok.addAction("OK");
      await ok.present();
    } else {
      const n = new Notification();
      n.title = "Ping sent";
      n.body = message;
      await n.schedule();
    }
  } catch (e) {
    const fail = new Alert();
    fail.title = "Failed to send";
    fail.message = String(e);
    fail.addAction("OK");
    await fail.present();
  }
}

await main();
Script.complete();
