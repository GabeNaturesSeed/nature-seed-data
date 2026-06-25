// Variables used by Scriptable.
// These must be at the very top of the file. Do not edit.
// icon-color: deep-blue; icon-glyph: trophy;

// worldcup-2026-bracket.js
// A "slowly fillable" 2026 World Cup knockout bracket tracker.
//
// HOW IT WORKS
// - The schedule scaffold (match numbers, dates, kickoff times, venues, and
//   who-plays-who slots like "1A", "2B", "3rd", "Winner of match 74") lives
//   in SCHEDULE below and never changes.
// - You fill in reality as it happens. Everything you type is saved to a JSON
//   file on the device, so it survives reruns and app updates.
//     * Tap a GROUP row  -> type the four teams in their final 1-4 order.
//       Group winners (1X) and runners-up (2X) then auto-appear in the bracket.
//     * Tap a MATCH with a "3rd ..." slot -> type which third-placed team got
//       assigned there (FIFA decides this once all groups finish).
//     * Tap any MATCH whose two teams are known -> pick who advances. The
//       winner automatically flows into the next round ("Winner of match N").
// - Re-tap to change or clear anything.
//
// DATA ACCURACY: dates/times/venues/pairings below were assembled from public
// schedules while the group stage was still running. Anything I could not fully
// confirm is marked with `v: 1` and shows a (check) flag in the app. Correct any
// of it directly in SCHEDULE — it's all in one place. Times are US Eastern (ET).
// Sources are listed in the README.

// ---------------------------------------------------------------------------
// SCHEDULE SCAFFOLD  (edit here if a detail is wrong)
// slot types: {w:'A'} winner of group A | {r:'A'} runner-up A
//             {p:['A','B','C']} a third-placed team from this pool
//             {m:74} winner of match 74
// ---------------------------------------------------------------------------
const GROUPS = ["A","B","C","D","E","F","G","H","I","J","K","L"];

const SCHEDULE = [
  // ----- Round of 32 (matches 73-88) -----
  { n:73, round:"Round of 32", a:{r:"A"}, b:{r:"B"}, date:"Sun Jun 28", et:"3:00pm", venue:"SoFi Stadium", city:"Los Angeles" },
  { n:74, round:"Round of 32", a:{w:"E"}, b:{p:["A","B","C","D","F"]}, date:"Mon Jun 29", et:"4:30pm", venue:"Gillette Stadium", city:"Foxborough" },
  { n:75, round:"Round of 32", a:{w:"F"}, b:{r:"C"}, date:"Mon Jun 29", et:"9:00pm", venue:"Estadio BBVA", city:"Monterrey" },
  { n:76, round:"Round of 32", a:{w:"C"}, b:{r:"F"}, date:"Mon Jun 29", et:"7:00pm", venue:"NRG Stadium", city:"Houston", v:1 },
  { n:77, round:"Round of 32", a:{w:"I"}, b:{p:["C","D","F","G","H"]}, date:"Tue Jun 30", et:"10:00pm", venue:"MetLife Stadium", city:"East Rutherford" },
  { n:78, round:"Round of 32", a:{r:"E"}, b:{r:"I"}, date:"Tue Jun 30", et:"6:00pm", venue:"AT&T Stadium", city:"Arlington" },
  { n:79, round:"Round of 32", a:{w:"A"}, b:{p:["C","E","F","H","I"]}, date:"Wed Jul 1", et:"10:00pm", venue:"Estadio Azteca", city:"Mexico City", v:1 },
  { n:80, round:"Round of 32", a:{w:"L"}, b:{p:["E","H","I","J","K"]}, date:"Wed Jul 1", et:"12:00pm", venue:"Mercedes-Benz Stadium", city:"Atlanta" },
  { n:81, round:"Round of 32", a:{w:"K"}, b:{p:["A","B","C","D","E","F","G","H","I","J","K","L"]}, date:"Wed Jul 1", et:"TBD", venue:"TBD", city:"TBD", v:1 },
  { n:82, round:"Round of 32", a:{w:"G"}, b:{p:["A","E","H","I","J"]}, date:"Thu Jul 2", et:"4:00pm", venue:"Lumen Field", city:"Seattle", v:1 },
  { n:83, round:"Round of 32", a:{w:"D"}, b:{p:["B","E","F","I","J"]}, date:"Thu Jul 2", et:"8:00pm", venue:"Levi's Stadium", city:"Santa Clara", v:1 },
  { n:84, round:"Round of 32", a:{w:"H"}, b:{r:"J"}, date:"Thu Jul 2", et:"3:00pm", venue:"SoFi Stadium", city:"Los Angeles", v:1 },
  { n:85, round:"Round of 32", a:{r:"K"}, b:{r:"L"}, date:"Fri Jul 3", et:"7:00pm", venue:"BMO Field", city:"Toronto", v:1 },
  { n:86, round:"Round of 32", a:{w:"B"}, b:{p:["E","F","G","I","J"]}, date:"Fri Jul 3", et:"11:00pm", venue:"BC Place", city:"Vancouver", v:1 },
  { n:87, round:"Round of 32", a:{r:"D"}, b:{r:"G"}, date:"Fri Jul 3", et:"2:00pm", venue:"AT&T Stadium", city:"Arlington", v:1 },
  { n:88, round:"Round of 32", a:{w:"J"}, b:{r:"H"}, date:"Fri Jul 3", et:"6:00pm", venue:"Hard Rock Stadium", city:"Miami Gardens", v:1 },

  // ----- Round of 16 (matches 89-96) -----
  { n:89, round:"Round of 16", a:{m:74}, b:{m:77}, date:"Sat Jul 4", et:"TBD", venue:"Lincoln Financial Field", city:"Philadelphia", v:1 },
  { n:90, round:"Round of 16", a:{m:73}, b:{m:75}, date:"Sat Jul 4", et:"TBD", venue:"NRG Stadium", city:"Houston", v:1 },
  { n:91, round:"Round of 16", a:{m:76}, b:{m:78}, date:"Sun Jul 5", et:"TBD", venue:"MetLife Stadium", city:"East Rutherford", v:1 },
  { n:92, round:"Round of 16", a:{m:79}, b:{m:80}, date:"Sun Jul 5", et:"TBD", venue:"Estadio Azteca", city:"Mexico City", v:1 },
  { n:93, round:"Round of 16", a:{m:83}, b:{m:84}, date:"Mon Jul 6", et:"TBD", venue:"AT&T Stadium", city:"Arlington", v:1 },
  { n:94, round:"Round of 16", a:{m:81}, b:{m:82}, date:"Mon Jul 6", et:"TBD", venue:"Lumen Field", city:"Seattle", v:1 },
  { n:95, round:"Round of 16", a:{m:86}, b:{m:88}, date:"Tue Jul 7", et:"TBD", venue:"Mercedes-Benz Stadium", city:"Atlanta", v:1 },
  { n:96, round:"Round of 16", a:{m:85}, b:{m:87}, date:"Tue Jul 7", et:"TBD", venue:"BC Place", city:"Vancouver", v:1 },

  // ----- Quarter-finals (matches 97-100) -----
  { n:97, round:"Quarter-final", a:{m:89}, b:{m:90}, date:"Thu Jul 9", et:"4:00pm", venue:"Gillette Stadium", city:"Foxborough" },
  { n:98, round:"Quarter-final", a:{m:93}, b:{m:94}, date:"Fri Jul 10", et:"3:00pm", venue:"SoFi Stadium", city:"Los Angeles" },
  { n:99, round:"Quarter-final", a:{m:91}, b:{m:92}, date:"Sat Jul 11", et:"5:00pm", venue:"Hard Rock Stadium", city:"Miami Gardens" },
  { n:100, round:"Quarter-final", a:{m:95}, b:{m:96}, date:"Sat Jul 11", et:"9:00pm", venue:"Arrowhead Stadium", city:"Kansas City" },

  // ----- Semi-finals (matches 101-102) -----
  { n:101, round:"Semi-final", a:{m:97}, b:{m:98}, date:"Tue Jul 14", et:"3:00pm", venue:"AT&T Stadium", city:"Arlington" },
  { n:102, round:"Semi-final", a:{m:99}, b:{m:100}, date:"Wed Jul 15", et:"3:00pm", venue:"Mercedes-Benz Stadium", city:"Atlanta" },

  // ----- Third place & Final -----
  { n:103, round:"Third place", a:{l:101}, b:{l:102}, date:"Sat Jul 18", et:"5:00pm", venue:"Hard Rock Stadium", city:"Miami Gardens" },
  { n:104, round:"Final", a:{m:101}, b:{m:102}, date:"Sun Jul 19", et:"3:00pm", venue:"MetLife Stadium", city:"East Rutherford" },
];

const ROUND_ORDER = ["Round of 32","Round of 16","Quarter-final","Semi-final","Third place","Final"];
const byNum = {};
for (const m of SCHEDULE) byNum[m.n] = m;

// ---------------------------------------------------------------------------
// PERSISTENT STATE  (everything you type)
// ---------------------------------------------------------------------------
const fm = FileManager.local();
const STATE_PATH = fm.joinPath(fm.documentsDirectory(), "wc2026-state.json");

function loadState() {
  try {
    if (fm.fileExists(STATE_PATH)) return JSON.parse(fm.readString(STATE_PATH));
  } catch (e) {}
  return { groups: {}, thirds: {}, results: {} };
}
function saveState(s) {
  fm.writeString(STATE_PATH, JSON.stringify(s));
}
let STATE = loadState();

// ---------------------------------------------------------------------------
// SLOT RESOLUTION
// ---------------------------------------------------------------------------
function teamName(s) { return (s && String(s).trim()) ? String(s).trim() : null; }

function slotLabel(slot) {
  if (slot.w) return slot.w + "1";          // winner of group
  if (slot.r) return slot.r + "2";          // runner-up of group
  if (slot.p) return "3rd " + slot.p.join("/");
  if (slot.m) return "W" + slot.m;          // winner of match
  if (slot.l) return "L" + slot.l;          // loser of match (3rd place game)
  return "TBD";
}

// Returns the actual team name for a slot, or null if not yet known.
function resolveSlot(matchNum, which, slot, depth) {
  depth = depth || 0;
  if (depth > 20) return null;
  if (slot.w) { const g = STATE.groups[slot.w]; return g ? teamName(g.p1) : null; }
  if (slot.r) { const g = STATE.groups[slot.r]; return g ? teamName(g.p2) : null; }
  if (slot.p) { return teamName((STATE.thirds[matchNum] || {})[which]); }
  if (slot.m) return resolveWinner(slot.m, depth + 1);
  if (slot.l) return resolveLoser(slot.l, depth + 1);
  return null;
}
function resolveWinner(n, depth) {
  const r = STATE.results[n];
  if (!r) return null;
  const m = byNum[n];
  return resolveSlot(n, r === "a" ? "a" : "b", r === "a" ? m.a : m.b, depth);
}
function resolveLoser(n, depth) {
  const r = STATE.results[n];
  if (!r) return null;
  const m = byNum[n];
  return resolveSlot(n, r === "a" ? "b" : "a", r === "a" ? m.b : m.a, depth);
}

function sideText(m, which) {
  const slot = which === "a" ? m.a : m.b;
  const team = resolveSlot(m.n, which, slot, 0);
  return { team, label: slotLabel(slot), text: team || slotLabel(slot) };
}

// ---------------------------------------------------------------------------
// EDIT ACTIONS
// ---------------------------------------------------------------------------
async function editGroup(g) {
  const cur = STATE.groups[g] || {};
  const a = new Alert();
  a.title = "Group " + g + " final standings";
  a.message = "Enter teams in finishing order. Leave blank if unknown.";
  a.addTextField("1st place", cur.p1 || "");
  a.addTextField("2nd place", cur.p2 || "");
  a.addTextField("3rd place", cur.p3 || "");
  a.addTextField("4th place", cur.p4 || "");
  a.addAction("Save");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return;
  STATE.groups[g] = {
    p1: a.textFieldValue(0), p2: a.textFieldValue(1),
    p3: a.textFieldValue(2), p4: a.textFieldValue(3),
  };
  saveState(STATE);
}

async function setThird(m, which) {
  const slot = which === "a" ? m.a : m.b;
  const a = new Alert();
  a.title = "Match " + m.n + " — 3rd-placed team";
  a.message = "Which third-placed team was assigned here?\nPool: " + slot.p.join(", ");
  a.addTextField("Team name", ((STATE.thirds[m.n] || {})[which]) || "");
  a.addAction("Save");
  a.addCancelAction("Cancel");
  if ((await a.presentAlert()) === -1) return;
  STATE.thirds[m.n] = STATE.thirds[m.n] || {};
  STATE.thirds[m.n][which] = a.textFieldValue(0);
  saveState(STATE);
}

async function editMatch(m) {
  const A = sideText(m, "a"), B = sideText(m, "b");
  const a = new Alert();
  a.title = "Match " + m.n + " — " + m.round;
  a.message = A.text + "  vs  " + B.text + "\n" + m.date + " · " + m.et + " ET · " + m.city;

  const actions = [];
  if (m.a.p) { a.addAction("Set 3rd-place team (left)"); actions.push("third-a"); }
  if (m.b.p) { a.addAction("Set 3rd-place team (right)"); actions.push("third-b"); }
  if (A.team && B.team) {
    a.addAction(A.team + " advances"); actions.push("win-a");
    a.addAction(B.team + " advances"); actions.push("win-b");
  }
  if (STATE.results[m.n]) { a.addDestructiveAction("Clear result"); actions.push("clear"); }
  a.addCancelAction("Close");

  const idx = await a.presentSheet();
  if (idx === -1) return;
  const choice = actions[idx];
  if (choice === "third-a") return setThird(m, "a");
  if (choice === "third-b") return setThird(m, "b");
  if (choice === "win-a") STATE.results[m.n] = "a";
  if (choice === "win-b") STATE.results[m.n] = "b";
  if (choice === "clear") delete STATE.results[m.n];
  saveState(STATE);
}

// ---------------------------------------------------------------------------
// RENDER
// ---------------------------------------------------------------------------
const COLORS = {
  header: new Color("#0a1f44"),
  round: new Color("#13315c"),
  win: new Color("#1b7f3b"),
  dim: new Color("#8a8a8a"),
  warn: new Color("#b8860b"),
};

function groupSummary(g) {
  const d = STATE.groups[g] || {};
  const parts = [];
  if (teamName(d.p1)) parts.push("1." + d.p1.trim());
  if (teamName(d.p2)) parts.push("2." + d.p2.trim());
  if (teamName(d.p3)) parts.push("3." + d.p3.trim());
  return parts.length ? parts.join("   ") : "tap to enter standings";
}

const table = new UITable();
table.showSeparators = true;

function buildTable() {
  table.removeAllRows();

  const title = new UITableRow();
  title.isHeader = true;
  title.backgroundColor = COLORS.header;
  const tc = title.addText("FIFA World Cup 2026", "Knockout bracket — tap to fill");
  tc.titleColor = Color.white();
  tc.subtitleColor = new Color("#cdd7e6");
  tc.titleFont = Font.boldSystemFont(18);
  table.addRow(title);

  // Groups section
  const gh = new UITableRow();
  gh.isHeader = true;
  gh.backgroundColor = COLORS.round;
  const ghc = gh.addText("Groups", "tap a group to set final 1-4 order");
  ghc.titleColor = Color.white();
  ghc.subtitleColor = new Color("#cdd7e6");
  table.addRow(gh);

  for (const g of GROUPS) {
    const row = new UITableRow();
    row.height = 46;
    const c = row.addText("Group " + g, groupSummary(g));
    c.titleFont = Font.boldSystemFont(15);
    if (!teamName((STATE.groups[g] || {}).p1)) c.subtitleColor = COLORS.dim;
    row.onSelect = () => editGroup(g).then(reload);
    table.addRow(row);
  }

  // Knockout rounds
  for (const round of ROUND_ORDER) {
    const matches = SCHEDULE.filter(m => m.round === round);
    if (!matches.length) continue;

    const rh = new UITableRow();
    rh.isHeader = true;
    rh.backgroundColor = COLORS.round;
    const rhc = rh.addText(round);
    rhc.titleColor = Color.white();
    table.addRow(rh);

    for (const m of matches) {
      const A = sideText(m, "a"), B = sideText(m, "b");
      const res = STATE.results[m.n];
      const flag = m.v ? "  (check)" : "";

      const row = new UITableRow();
      row.height = 58;

      const numCell = row.addText("#" + m.n);
      numCell.widthWeight = 14;
      numCell.titleColor = COLORS.dim;
      numCell.titleFont = Font.systemFont(11);

      const matchup = A.text + "   v   " + B.text;
      const sub = m.date + " · " + (m.et === "TBD" ? "time TBD" : m.et + " ET") + " · " + m.venue + ", " + m.city + flag;
      const mc = row.addText(matchup, sub);
      mc.widthWeight = 72;
      mc.titleFont = res ? Font.boldSystemFont(15) : Font.systemFont(15);
      if (res) {
        mc.titleColor = COLORS.win;
      } else if (!A.team && !B.team) {
        mc.titleColor = COLORS.dim;
      }
      if (m.v) mc.subtitleColor = COLORS.warn;

      const winner = res ? (res === "a" ? A.text : B.text) : "";
      const wc = row.addText(res ? "won" : "", res ? winner : "");
      wc.widthWeight = 14;
      wc.titleColor = COLORS.win;
      wc.titleFont = Font.systemFont(10);
      wc.subtitleColor = COLORS.win;
      wc.subtitleFont = Font.boldSystemFont(11);

      row.onSelect = () => editMatch(m).then(reload);
      table.addRow(row);
    }
  }
}

async function reload() {
  STATE = loadState();
  buildTable();
  table.reload();
}

buildTable();
await table.present();
Script.complete();
