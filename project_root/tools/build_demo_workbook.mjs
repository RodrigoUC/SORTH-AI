// Optional authoring tool: Node.js with @oai/artifact-tool 2.8.58 or newer.
// Usage: node build_demo_workbook.mjs <project_root> [preview-directory]
// The application and its tests do not require this authoring dependency.
import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root = path.resolve(process.argv[2] ?? '.');
const previewDir = process.argv[3];
const sheets = JSON.parse(await fs.readFile(path.join(root, 'data/input/demo_source.json'), 'utf8'));
const workbook = Workbook.create();
for (const [name, rows] of Object.entries(sheets)) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const lastColumn = String.fromCharCode(64 + rows[0].length);
  const range = sheet.getRange(`A1:${lastColumn}${rows.length}`);
  range.values = rows;
  range.format.font = { name: 'Arial', size: 11, color: '#183153' };
  range.format.rowHeight = 22;
  range.format.verticalAlignment = 'center';
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: '#183153', font: { name: 'Arial', size: 11, bold: true, color: '#FFFFFF' },
    rowHeight: 30,
  };
  range.format.autofitColumns();
  sheet.getRange('A:A').format.columnWidth = 18;
  sheet.getRange('B:B').format.columnWidth = 45;
  sheet.getRange('C:C').format.columnWidth = 16;
  if (name === 'Cursos') {
    sheet.getRange('D:E').format.columnWidth = 18;
    sheet.getRange('F:F').format.columnWidth = 10;
  }
  sheet.getRange(name === 'Cursos' ? 'C:C' : 'D:E').format.columnWidth = 24;
  sheet.freezePanes.freezeRows(1);
  sheet.tables.add(`A1:${lastColumn}${rows.length}`, true, `Demo${name}`);
}
workbook.recalculate();
console.log((await workbook.inspect({ kind: 'sheet,table', maxChars: 3000, tableMaxRows: 3 })).ndjson);
for (const name of Object.keys(sheets)) {
  if (previewDir) {
    await fs.mkdir(previewDir, { recursive: true });
    const preview = await workbook.render({ sheetName: name, range: name === 'Aulas' ? 'A1:E9' : 'A1:F13', scale: 1.5 });
    await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}
await (await SpreadsheetFile.exportXlsx(workbook)).save(path.join(root, 'data/input/Cursos_Ejemplo.xlsx'));
