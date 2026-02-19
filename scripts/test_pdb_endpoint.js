/**
 * Test script for the frame PDB endpoint.
 * Run with: node scripts/test_pdb_endpoint.js
 * Requires: backend running on port 5001, systems/1ULL/frame_1/ to exist
 */
const http = require('http')

const SYSTEM_ID = process.argv[2] || '1ULL'
const FRAME = 1
const URL = `http://localhost:5001/api/systems/${SYSTEM_ID}/frame/${FRAME}/pdb`

console.log('Testing PDB endpoint:', URL)
console.log('')

http.get(URL, (res) => {
  let data = ''
  res.on('data', chunk => { data += chunk })
  res.on('end', () => {
    console.log('Status:', res.statusCode)
    console.log('Content-Type:', res.headers['content-type'])
    console.log('Body length:', data.length, 'chars')
    if (data.length > 0) {
      const firstLine = data.split('\n')[0]
      console.log('First line:', firstLine.substring(0, 60) + '...')
      if (data.includes('ATOM') || data.includes('HETATM')) {
        console.log('OK: PDB content detected')
      } else {
        console.log('WARN: No ATOM/HETATM lines - might be JSON error:', data.substring(0, 200))
      }
    }
    process.exit(res.statusCode === 200 ? 0 : 1)
  })
}).on('error', (err) => {
  console.error('Request failed:', err.message)
  console.error('Is the backend running on port 5001?')
  process.exit(1)
})
