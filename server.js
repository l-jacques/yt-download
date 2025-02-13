const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const port = process.env.PORT || 3000;
const downloadDir = '/downloads';

let downloadStatus = {};

const statusEmojis = {
    'in progress': '⏳',
    'Downloaded': '✅',
    'Error': '❌',
    'Stderr': '⚠️'
};

app.use(express.json());
app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.post('/download', (req, res) => {
    const url = req.body.url;
    const downloadId = uuidv4();
    downloadStatus[downloadId] = { status: 'in progress', title: '', filePath: '', started: new Date(), ended : null, errored: null };

    const infoCommand = `yt-dlp --get-title ${url}`;
    exec(infoCommand, (infoError, title) => {
        if (infoError) {
            console.error(`Error: ${infoError.message}`);
            downloadStatus[downloadId] = { status: `Error: ${infoError.message}`, title: '', filePath: '' };
            return;
        }

        downloadStatus[downloadId].title = title.trim();
        const downloadCommand = `yt-dlp -o "${downloadDir}/%(title)s.%(ext)s" ${url}`;

        exec(downloadCommand, (error, stdout, stderr) => {
            if (error) {

                console.error(`Error: ${error.message}`);
                downloadStatus[downloadId].errored = new Date();
                downloadStatus[downloadId].status = `Error: ${error.message}`;
                return;
            }

            if (stderr) {
                console.error(`Stderr: ${stderr}`);
                downloadStatus[downloadId].errored = new Date();
                downloadStatus[downloadId].status = `Stderr: ${stderr}`;
                return;
            }

            console.log(`Stdout: ${stdout}`);
            downloadStatus[downloadId].status = 'Downloaded';
            downloadStatus[downloadId].ended = new Date();
            downloadStatus[downloadId].filePath = path.join(downloadDir, `${downloadStatus[downloadId].title}.${stdout.split('.').pop()}`);
        });

        res.send({ downloadId, message: 'Download started', title: downloadStatus[downloadId].title });
    });
});

app.get('/statusPage', (req, res) => {
    let html = '<html><head><title>Download Status</title></head><body>';
    html += '<h1>Download Status</h1><ul>';

    for (const [downloadId, status] of Object.entries(downloadStatus)) {
        const emoji = statusEmojis[status.status.split(':')[0]] || '❓';
        html += `<li>${emoji} <strong>${status.title}</strong>: ${status.status}</li>`;
    }

    html += '</ul></body></html>';
    res.send(html);
});

app.get('/status', (req, res) => {
    let json = [];
    for (const [downloadId, status] of Object.entries(downloadStatus)) {
        json.push( status );
    }
    res.send(json);
});
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
