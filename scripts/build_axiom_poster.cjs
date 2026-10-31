const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const root = path.resolve(__dirname, '..');
const visualPath = path.join(root, 'event-dashboard', 'src', 'assets', 'project-axiom-key-visual.png');
const outDir = path.join(root, 'output', 'project-axiom');
fs.mkdirSync(outDir, { recursive: true });
const visual = fs.readFileSync(visualPath).toString('base64');

const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <defs>
    <linearGradient id="veil" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#040b20" stop-opacity=".98"/>
      <stop offset=".43" stop-color="#040b20" stop-opacity=".88"/>
      <stop offset=".72" stop-color="#040b20" stop-opacity=".2"/>
      <stop offset="1" stop-color="#040b20" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="bottom" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#040b20" stop-opacity="0"/>
      <stop offset="1" stop-color="#040b20" stop-opacity=".94"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" x2="1">
      <stop stop-color="#d8ff67"/><stop offset="1" stop-color="#86acff"/>
    </linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect width="1080" height="1350" fill="#040b20"/>
  <image href="data:image/png;base64,${visual}" width="1080" height="1350" preserveAspectRatio="xMidYMid slice"/>
  <rect width="1080" height="1350" fill="url(#veil)"/>
  <rect y="970" width="1080" height="380" fill="url(#bottom)"/>
  <text x="70" y="82" fill="#d8ff67" font-family="Arial,sans-serif" font-size="15" font-weight="700" letter-spacing="5">CORE MEMBERS ONLY · AN INTERNAL INITIATIVE</text>
  <text x="66" y="235" fill="#f8f5eb" font-family="Arial,sans-serif" font-size="105" font-weight="800" letter-spacing="-6">PROJECT</text>
  <text x="68" y="342" fill="#8eb1ff" font-family="Georgia,serif" font-size="126" font-weight="700" font-style="italic">Axiom.</text>
  <rect x="70" y="398" width="74" height="6" rx="3" fill="url(#accent)" filter="url(#glow)"/>
  <text x="70" y="474" fill="#f8f5eb" font-family="Arial,sans-serif" font-size="34" font-weight="700">Most clubs ask members to volunteer.</text>
  <text x="70" y="522" fill="#d8ff67" font-family="Arial,sans-serif" font-size="34" font-weight="700">We’re asking ours to build.</text>
  <text x="70" y="611" fill="#c2cbe0" font-family="Arial,sans-serif" font-size="22">
    <tspan x="70" dy="0">An internal space for the core members of</tspan>
    <tspan x="70" dy="34">Club Asymptotes to pursue either research</tspan>
    <tspan x="70" dy="34">or a product — together, for the club.</tspan>
  </text>
  <g transform="translate(70 1030)">
    <text fill="#f8f5eb" font-family="Arial,sans-serif" font-size="27" font-weight="700">
      <tspan x="0" dy="0">Because a community grows strongest</tspan>
      <tspan x="0" dy="40">when its people create, not only coordinate.</tspan>
    </text>
    <line x1="0" x2="940" y1="112" y2="112" stroke="#ffffff" stroke-opacity=".2"/>
    <text x="0" y="163" fill="#94a1bf" font-family="Arial,sans-serif" font-size="14" font-weight="700" letter-spacing="4">THINK · BUILD · SHARE · GROW</text>
    <text x="940" y="163" text-anchor="end" fill="#d8ff67" font-family="Arial,sans-serif" font-size="14" font-weight="700" letter-spacing="3">BUILT FROM WITHIN</text>
  </g>
</svg>`;

const svgPath = path.join(outDir, 'project-axiom-launch-poster.svg');
const pngPath = path.join(outDir, 'project-axiom-launch-poster.png');
fs.writeFileSync(svgPath, svg);
sharp(Buffer.from(svg)).png().toFile(pngPath).then(() => {
  process.stdout.write(`${pngPath}\n${svgPath}\n`);
});
