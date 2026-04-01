const path = require('node:path');

const BASE_URL = 'http://localhost:3000';
// const SERVER_PATH = path.join(__dirname, '..', 'server-local.js');
const SERVER_PATH = path.join(__dirname, 'dummy-server.js');

module.exports = { BASE_URL, SERVER_PATH };
