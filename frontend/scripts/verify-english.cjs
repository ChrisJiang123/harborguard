const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const ts = require('typescript')
const compiled = path.join(__dirname, '../work/verify-english')
fs.writeFileSync(path.join(compiled, 'package.json'), '{"type":"commonjs"}\n')
const { englishText } = require(path.join(compiled, 'english.js'))
const root = path.join(__dirname, '..')
const hasHan = text => /\p{Script=Han}/u.test(text)
let checked = 0

function checkSource(directory) {
  for (const file of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, file.name)
    if (file.isDirectory()) checkSource(filename)
    else if (/\.tsx?$/.test(filename) && !filename.endsWith(path.join('data', 'english.ts'))) {
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
    checked++
  } else if (value && typeof value === 'object') Object.values(value).forEach(item => checkData(item, filename, translate))
}

checkSource(path.join(root, 'src'))
for (const filename of ['demo_a.jsonl', 'demo_b.jsonl', 'demo_full.jsonl', 'replay_a.jsonl', 'replay_b.jsonl']) {
  for (const line of fs.readFileSync(path.join(root, 'public', filename), 'utf8').trim().split(/\r?\n/)) checkData(JSON.parse(line), filename, filename.startsWith('replay_'))
}
for (const filename of ['assets.json', 'zones.geojson']) checkData(JSON.parse(fs.readFileSync(path.join(root, 'public/data', filename), 'utf8')), filename, true)
assert.equal(englishText('T1'), 'T1')
assert.match(fs.readFileSync(path.join(root, 'index.html'), 'utf8'), /<html lang="en">/)
console.log(`PASS English UI: ${checked} source/data strings checked; UI, demo replays, and known recorded source messages display in English; source IDs are preserved.`)
