function parseCSV(csvText) {
    const rows = [];
    const headers = [];
    let currentRow = [];
    let currentField = '';
    let inQuotes = false;
    let isFirstRow = true;

    for (let i = 0; i < csvText.length; i++) {
        const char = csvText[i];
        const nextChar = csvText[i + 1];

        if (inQuotes) {
            if (char === '"') {
                if (nextChar === '"') {
                    currentField += '"';
                    i += 1;
                } else {
                    inQuotes = false;
                }
            } else {
                currentField += char;
            }
        } else if (char === '"') {
            inQuotes = true;
        } else if (char === ',') {
            currentRow.push(currentField);
            currentField = '';
        } else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
            if (char === '\r') i += 1;
            currentRow.push(currentField);
            currentField = '';

            if (isFirstRow) {
                headers.push(...currentRow);
                isFirstRow = false;
            } else if (currentRow.length > 0 && currentRow.some((field) => field.trim() !== '')) {
                const rowObj = {};
                headers.forEach((header, idx) => {
                    rowObj[header] = currentRow[idx] || '';
                });
                rows.push(rowObj);
            }
            currentRow = [];
        } else if (char !== '\r') {
            currentField += char;
        }
    }

    if (currentField !== '' || currentRow.length > 0) {
        currentRow.push(currentField);
        if (currentRow.length > 0 && currentRow.some((field) => field.trim() !== '')) {
            const rowObj = {};
            headers.forEach((header, idx) => {
                rowObj[header] = currentRow[idx] || '';
            });
            rows.push(rowObj);
        }
    }

    return rows;
}

module.exports = { parseCSV };
