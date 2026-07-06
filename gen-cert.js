// Generate self-signed SSL certificate for LAN HTTPS access
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const certDir = path.join(__dirname, 'certs');

if (!fs.existsSync(certDir)) {
  fs.mkdirSync(certDir, { recursive: true });
}

const keyPath = path.join(certDir, 'key.pem');
const certPath = path.join(certDir, 'cert.pem');

// Try using OpenSSL
try {
  console.log('🔐 Generating self-signed SSL certificate...');
  execSync(
    `openssl req -x509 -newkey rsa:2048 -keyout "${keyPath}" -out "${certPath}" -days 365 -nodes -subj "/CN=localhost/O=GameDev2026"`,
    { stdio: 'inherit' }
  );
  console.log('✅ Certificate generated successfully!');
  console.log(`   Key:  ${keyPath}`);
  console.log(`   Cert: ${certPath}`);
  console.log('');
  console.log('Now run: npm run dev');
} catch (e) {
  // Fallback: generate using Node.js (requires Node 15+)
  try {
    const { generateKeyPairSync, createCertificate } = require('crypto');
    console.log('⚠️  OpenSSL not found. Trying Node.js crypto...');
    
    // Node.js doesn't have a built-in X509 cert generator easily,
    // so we'll use a minimal approach with the selfsigned package
    console.log('');
    console.log('❌ OpenSSL is not installed on this system.');
    console.log('');
    console.log('To fix, either:');
    console.log('  1. Install OpenSSL: https://slproweb.com/products/Win32OpenSSL.html');
    console.log('  2. Or just use http://localhost:8080 (works without HTTPS)');
    console.log('');
  } catch (e2) {
    console.log('❌ Could not generate certificate.');
    console.log('   Just use http://localhost:8080 instead.');
  }
}
