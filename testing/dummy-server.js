const http = require('http');

const PORT = 4000;

const handler = (req, res) => {
    if (req.url === '/ping') {
        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('hello world');
    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('not found');
    }
}

const server = http.createServer(handler);

server.listen(PORT, () => {
    console.log(`Dummy server is listening on http://localhost:${PORT}`);
});

module.exports = server;