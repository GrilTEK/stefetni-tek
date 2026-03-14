const path = require('path');
const fs   = require('fs');
const src  = path.resolve(__dirname, '../../frontend');
const dest = path.resolve(__dirname, '../www');
if (!fs.existsSync(dest)) {
  fs.symlinkSync(src, dest, 'dir');
  console.log('Created symlink: mobile/www -> ../frontend');
} else {
  console.log('Symlink already exists.');
}
