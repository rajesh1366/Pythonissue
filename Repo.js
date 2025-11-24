// toExcel.js
const ExcelJS = require('exceljs');
const data = require('./data.js'); // adjust path

async function writeXlsx(rows) {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet('Sheet1');

  if (rows.length === 0) {
    await wb.xlsx.writeFile('output.xlsx');
    console.log('Written output.xlsx (no rows)');
    return;
  }

  // Add header row from keys of first object
  const headers = Object.keys(rows[0]);
  ws.addRow(headers);

  // Add each row in same key order
  rows.forEach(obj => {
    ws.addRow(headers.map(h => obj[h]));
  });

  await wb.xlsx.writeFile('output.xlsx');
  console.log('Written output.xlsx');
}

writeXlsx(data).catch(console.error);
