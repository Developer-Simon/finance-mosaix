const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const pngToIco = require('png-to-ico');

(async () => {
  const svgFile = path.resolve(__dirname, '../docs/img/favicon.svg');
  const pngFile = path.resolve(__dirname, '../docs/img/favicon-256.png');
  const icoFile = path.resolve(__dirname, '../docs/img/favicon.ico');

  if (!fs.existsSync(svgFile)) {
    throw new Error(`SVG source not found: ${svgFile}`);
  }

  await sharp(svgFile)
    .resize(256, 256)
    .png()
    .toFile(pngFile);

  const icoBuffer = await pngToIco(pngFile);
  fs.writeFileSync(icoFile, icoBuffer);
  console.log(`Created ${icoFile}`);
})();
