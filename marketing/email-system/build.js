const mjml2html = require('mjml');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const TEMPLATES_DIR = path.join(ROOT, 'templates');
const DIST_DIR = path.join(ROOT, 'dist');
const WARN_KB = 90;
const LIMIT_KB = 102;

function compile(templatePath) {
  const input = fs.readFileSync(templatePath, 'utf8');
  const { html, errors } = mjml2html(input, {
    filePath: templatePath,
    validationLevel: 'strict'
  });

  if (errors.length) {
    console.error(`[ERROR] ${path.basename(templatePath)}:`);
    errors.forEach(e => console.error(`  ${e.formattedMessage}`));
    return false;
  }

  if (!fs.existsSync(DIST_DIR)) fs.mkdirSync(DIST_DIR, { recursive: true });

  const outName = path.basename(templatePath, '.mjml') + '.html';
  const outPath = path.join(DIST_DIR, outName);
  fs.writeFileSync(outPath, html);

  const sizeKB = Math.round(fs.statSync(outPath).size / 1024);

  if (sizeKB > LIMIT_KB) {
    console.error(`[CLIP]  ${outName} → ${sizeKB}KB — GMAIL WILL CLIP THIS (limit: ${LIMIT_KB}KB)`);
  } else if (sizeKB > WARN_KB) {
    console.warn(`[WARN]  ${outName} → ${sizeKB}KB — approaching Gmail limit (${LIMIT_KB}KB)`);
  } else {
    console.log(`[OK]    ${outName} → ${sizeKB}KB`);
  }

  return true;
}

function buildAll() {
  if (!fs.existsSync(TEMPLATES_DIR)) {
    console.log('No templates/ directory yet — nothing to compile.');
    return;
  }
  const templates = fs.readdirSync(TEMPLATES_DIR).filter(f => f.endsWith('.mjml'));
  if (!templates.length) {
    console.log('No .mjml files in templates/ yet.');
    return;
  }
  let ok = 0;
  templates.forEach(f => {
    if (compile(path.join(TEMPLATES_DIR, f))) ok++;
  });
  console.log(`\nBuilt ${ok}/${templates.length} templates.`);
}

buildAll();

if (process.argv.includes('--watch')) {
  console.log('\nWatching components/ and templates/ for changes...');
  const watchDirs = [TEMPLATES_DIR, path.join(ROOT, 'components')];
  watchDirs.forEach(dir => {
    if (!fs.existsSync(dir)) return;
    fs.watch(dir, { recursive: true }, (event, filename) => {
      if (filename && filename.endsWith('.mjml')) {
        console.log(`\n[CHANGE] ${filename} — rebuilding...`);
        buildAll();
      }
    });
  });
}
