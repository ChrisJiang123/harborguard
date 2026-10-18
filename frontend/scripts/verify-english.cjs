const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const compiled = path.join(__dirname, '../work/verify-english')
fs.writeFileSync(path.join(compiled, 'package.json'), '{"type":"commonjs"}\n')
const { englishText, englishDisplayValue, ENGLISH_UNAVAILABLE } = require(path.join(compiled, 'english.js'))
const { LEGACY_SOURCE_TEXT } = require(path.join(compiled, 'legacyEnglish.js'))
const root = path.join(__dirname, '..')
const hasHan = text => /\p{Script=Han}/u.test(text)
let checked = 0

function checkSource(directory) {
  for (const file of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, file.name)
    if (file.isDirectory()) checkSource(filename)
    else if (/\.tsx?$/.test(filename) && !['english.ts','legacyEnglish.ts'].some(name => filename.endsWith(path.join('data', name)))) {
      const source = ts.createSourceFile(filename, fs.readFileSync(filename, 'utf8'), ts.ScriptTarget.Latest, true, filename.endsWith('tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
      function check(text) { assert.equal(hasHan(text), false, `Untranslated UI text in ${filename}: ${text}`); checked++ }
      function visit(node) {
        if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) || ts.isJsxText(node)) check(node.text)
        if (ts.isTemplateExpression(node)) { check(node.head.text); node.templateSpans.forEach(span => check(span.literal.text)) }
        ts.forEachChild(node, visit)
      }
      visit(source)
    }
  }
}

function checkData(value, filename, translate) {
  if (typeof value === 'string') {
    assert.equal(hasHan(translate ? englishText(value) : value), false, `Untranslated display text in ${filename}: ${value}`)
    if(translate && hasHan(value)) assert.notEqual(englishText(value),ENGLISH_UNAVAILABLE,`Known source text needs an actual translation: ${value}`)
    checked++
  } else if (value && typeof value === 'object') Object.values(value).forEach(item => checkData(item, filename, translate))
}

checkSource(path.join(root, 'src'))
Object.values(LEGACY_SOURCE_TEXT).forEach(text => assert.equal(hasHan(text),false))
const legacy=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/legacy-language.json'),'utf8'))
const before=JSON.stringify(legacy)
legacy.source_text.forEach(text => checkData(text,'legacy live Agent/log fixture',true))
const rendered=englishDisplayValue(legacy.metrics)
checkData(rendered,'nested metric display',false)
assert.ok(!JSON.stringify(rendered).includes(ENGLISH_UNAVAILABLE),'all captured historical metric notes require an actual translation')
assert.equal(JSON.stringify(legacy),before,'English display must not mutate source records or metrics')
// Compare every numeric leaf, including archived failed results and denominators.
function numericLeaves(value) {
  if(typeof value==='number') return [value]
  if(value && typeof value==='object') return Object.values(value).flatMap(numericLeaves)
  return []
}
assert.deepEqual(numericLeaves(rendered),numericLeaves(legacy.metrics))
assert.equal(englishText('A newly generated English recommendation.'),'A newly generated English recommendation.')
assert.equal(englishText('\u672a\u6536\u5f55\u7684\u52a8\u6001\u6d88\u606f'),ENGLISH_UNAVAILABLE,'unknown prose must be explicit, never fabricated or leaked untranslated')
assert.equal(englishText('Submitted cloud/security recommendation rec-new (A7 → opt-2, 123 ms)'), 'Submitted cloud/security recommendation rec-new (A7 → opt-2, 123 ms)')
assert.equal(englishText('\u6d6e\u6807 B9 \u72b6\u6001\u5f02\u5e38\uff0c\u9700\u6838\u5b9e\u91cf\u7a0b\u76f8\u4ea4\u5206\u533a\u8986\u76d6'),'Buoy B9 has an abnormal status; verify coverage in zones intersecting its nominal range.')
for (const filename of ['demo_a.jsonl', 'demo_b.jsonl', 'demo_full.jsonl', 'replay_a.jsonl', 'replay_b.jsonl']) {
  for (const line of fs.readFileSync(path.join(root, 'public', filename), 'utf8').trim().split(/\r?\n/)) checkData(JSON.parse(line), filename, filename.startsWith('replay_'))
}
for (const filename of ['assets.json', 'zones.geojson']) checkData(JSON.parse(fs.readFileSync(path.join(root, 'public/data', filename), 'utf8')), filename, true)
assert.equal(englishText('T1'), 'T1')
assert.match(fs.readFileSync(path.join(root, 'index.html'), 'utf8'), /<html lang="en">/)
console.log(`PASS English UI: ${checked} source/data strings checked; UI, demo replays, and known recorded source messages display in English; source IDs are preserved.`)
