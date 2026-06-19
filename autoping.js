const https = require('https');

const url = 'https://reversed-unz3.onrender.com';
const interval = 5000; // 5 ثواني

console.log(`Starting autoping for ${url} every 5 seconds...`);

setInterval(() => {
  https.get(url, (res) => {
    console.log(`[${new Date().toISOString()}] Pinged ${url} - Status: ${res.statusCode}`);
    
    // تفريغ البيانات لتجنب تسرب الذاكرة (Memory Leak)
    res.on('data', () => {});
    res.on('end', () => {});
  }).on('error', (err) => {
    console.error(`[${new Date().toISOString()}] Error pinging ${url}: ${err.message}`);
  });
}, interval);
