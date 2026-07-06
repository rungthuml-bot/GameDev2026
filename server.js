const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const os = require('os');
const https = require('https');

// ── Config ──
const DOCS_DIR = path.join(__dirname, 'docs');
const PORT = 8080;

// ── MIME types ──
const MIME = {
  '.html': 'text/html', '.js': 'application/javascript',
  '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.gif': 'image/gif',
  '.svg': 'image/svg+xml', '.wav': 'audio/wav', '.mp3': 'audio/mpeg',
  '.ogg': 'audio/ogg', '.wasm': 'application/wasm',
  '.pck': 'application/octet-stream', '.ico': 'image/x-icon',
  '.import': 'text/plain',
};

// ── Get LAN IP ──
function getLanIP() {
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      if (net.family === 'IPv4' && !net.internal) return net.address;
    }
  }
  return null;
}

// ── Organize files into subdirectories ──
function organizeFiles() {
  console.log('  📁 กำลังจัดระเบียบไฟล์แล็ปต่างๆ ให้เป็นระบบ...');
  
  const folders = {
    'lab01': 'Lab01',
    'lab02-1': ['game21', 'Lab02-1'],
    'lab02-2': 'Lab02-2',
    'lab03': 'Lab03',
    'lab04': 'Lab04',
    'lab05': 'Lab05',
    'lab06': 'Lab06'
  };

  // Create folders if they don't exist
  for (const folder of Object.keys(folders)) {
    const folderPath = path.join(DOCS_DIR, folder);
    if (!fs.existsSync(folderPath)) {
      fs.mkdirSync(folderPath, { recursive: true });
    }
  }

  // Read all files in docs
  const files = fs.readdirSync(DOCS_DIR);

  for (const file of files) {
    const filePath = path.join(DOCS_DIR, file);
    
    // Skip directories and key files
    if (fs.statSync(filePath).isDirectory()) continue;
    if (file === 'index.html' || file === '.gitattributes' || file === 'project.godot') continue;

    // Check which folder the file belongs to
    let targetFolder = null;
    for (const [folder, prefixes] of Object.entries(folders)) {
      const prefixList = Array.isArray(prefixes) ? prefixes : [prefixes];
      for (const prefix of prefixList) {
        if (file.startsWith(prefix)) {
          targetFolder = folder;
          break;
        }
      }
      if (targetFolder) break;
    }

    if (targetFolder) {
      const destPath = path.join(DOCS_DIR, targetFolder, file);
      try {
        fs.renameSync(filePath, destPath);
        console.log(`    ➡️  ย้าย ${file} ไปยัง docs/${targetFolder}/`);
      } catch (err) {
        console.error(`    ❌ ย้าย ${file} ล้มเหลว:`, err.message);
      }
    }
  }
}

// ── Download game21 files from GitHub ──
const FILES_TO_DOWNLOAD = [
  'game21.html',
  'game21.js',
  'game21.pck',
  'game21.png',
  'game21.icon.png',
  'game21.apple-touch-icon.png',
  'game21.audio.worklet.js',
  'game21.audio.position.worklet.js'
];

function downloadFile(filename, folder) {
  const dest = path.join(DOCS_DIR, folder, filename);
  const url = `https://raw.githubusercontent.com/rungthuml-bot/gamedev2026project/main/docs/${filename}`;

  return new Promise((resolve, reject) => {
    console.log(`  📥 กำลังดาวน์โหลด: ${filename} ไปยัง docs/${folder}/...`);
    const file = fs.createWriteStream(dest);
    https.get(url, (response) => {
      if (response.statusCode !== 200) {
        fs.unlink(dest, () => {});
        reject(new Error(`Failed to download ${filename}: status code ${response.statusCode}`));
        return;
      }
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log(`  ✅ ดาวน์โหลดสำเร็จ: ${filename}`);
        resolve();
      });
    }).on('error', (err) => {
      fs.unlink(dest, () => {});
      reject(err);
    });
  });
}

async function syncGame21Files() {
  console.log('\n  ⚙️  กำลังตรวจสอบไฟล์ของ Lab 2.1 (game21)...');

  const wasmDest = path.join(DOCS_DIR, 'lab02-1', 'game21.wasm');
  const wasmSource = path.join(DOCS_DIR, 'lab01', 'Lab01.wasm');
  if (!fs.existsSync(wasmDest)) {
    if (fs.existsSync(wasmSource)) {
      console.log('  📦 กำลังคัดลอกไฟล์ engine wasm (game21.wasm)...');
      try {
        fs.copyFileSync(wasmSource, wasmDest);
        console.log('  ✅ คัดลอก game21.wasm สำเร็จ');
      } catch (err) {
        console.error('  ❌ คัดลอก game21.wasm ล้มเหลว:', err.message);
      }
    } else {
      console.log('  ⚠️  ไม่พบ Lab01.wasm สำหรับคัดลอกเป็น game21.wasm');
    }
  }

  // Download other files
  for (const filename of FILES_TO_DOWNLOAD) {
    const filePath = path.join(DOCS_DIR, 'lab02-1', filename);
    if (!fs.existsSync(filePath)) {
      try {
        await downloadFile(filename, 'lab02-1');
      } catch (err) {
        console.error(`  ❌ ดาวน์โหลด ${filename} ล้มเหลว:`, err.message);
      }
    }
  }
  console.log('  ✨ ตรวจสอบไฟล์เสร็จสิ้น\n');
}

// ── Request handler ──
function handleRequest(req, res) {
  // Required headers for Godot Web Export (SharedArrayBuffer, etc.)
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');

  const urlPath = decodeURIComponent(req.url.split('?')[0]);
  const filePath = path.join(DOCS_DIR, urlPath === '/' ? 'index.html' : urlPath);

  // Security: prevent directory traversal
  if (!filePath.startsWith(DOCS_DIR)) {
    res.writeHead(403); res.end('Forbidden'); return;
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(err.code === 'ENOENT' ? 404 : 500);
      res.end(err.code === 'ENOENT' ? 'Not Found' : 'Server Error');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
}

// ── Start server ──
const server = http.createServer(handleRequest);

server.listen(PORT, async () => {
  const lanIP = getLanIP();
  const localURL = `http://localhost:${PORT}`;

  console.log('');
  console.log('  ╔══════════════════════════════════════════════════════╗');
  console.log('  ║         🎮  Game Dev 2026 — Lab Server  🎮          ║');
  console.log('  ╠══════════════════════════════════════════════════════╣');
  console.log(`  ║  ✅ Local  → ${localURL}                    ║`);
  if (lanIP) {
  console.log(`  ║  ⚠️  LAN   → http://${lanIP}:${PORT}  (ไม่รองรับ Godot) ║`);
  }
  console.log('  ╠══════════════════════════════════════════════════════╣');
  console.log('  ║  💡 ต้องใช้ localhost เท่านั้น (Secure Context)     ║');
  console.log('  ║  💡 หรือใช้ GitHub Pages สำหรับแชร์ออนไลน์          ║');
  console.log('  ╚══════════════════════════════════════════════════════╝');
  console.log('');
  console.log('  กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์');
  console.log('');

  // 1. Organize files
  organizeFiles();

  // 2. Run the sync function
  await syncGame21Files();

  // Auto-open browser to localhost
  const openCmd = process.platform === 'win32' ? 'start' :
                  process.platform === 'darwin' ? 'open' : 'xdg-open';
  exec(`${openCmd} ${localURL}`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\n  ❌ พอร์ต ${PORT} ถูกใช้งานอยู่แล้ว`);
    console.error(`  ลองปิดโปรแกรมอื่นที่ใช้พอร์ต ${PORT} หรือเปลี่ยนพอร์ต\n`);
  } else {
    console.error(err);
  }
  process.exit(1);
});

