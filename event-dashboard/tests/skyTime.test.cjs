const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const esbuild = require('esbuild');

const code = esbuild.buildSync({
  entryPoints: [path.join(__dirname, '..', 'src', 'axiom', 'skyTime.ts')],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  write: false,
}).outputFiles[0].text;
const moduleUnderTest = { exports: {} };
vm.runInNewContext(code, { module: moduleUnderTest, exports: moduleUnderTest.exports, Date, Intl });
const { getSkyClock, msUntilNextMinute } = moduleUnderTest.exports;

test('sky phases switch at the intended IST boundaries', () => {
  const cases = [
    ['2026-11-08T23:59:00Z', 'night', 329],
    ['2026-11-09T00:00:00Z', 'morning', 330],
    ['2026-11-09T06:29:00Z', 'morning', 719],
    ['2026-11-09T06:30:00Z', 'afternoon', 720],
    ['2026-11-09T10:59:00Z', 'afternoon', 989],
    ['2026-11-09T11:00:00Z', 'evening', 990],
    ['2026-11-09T13:44:00Z', 'evening', 1154],
    ['2026-11-09T13:45:00Z', 'night', 1155],
  ];
  for (const [utcInstant, phase, minutes] of cases) {
    const result = getSkyClock(new Date(utcInstant));
    assert.equal(result.phase, phase, utcInstant);
    assert.equal(result.minutes, minutes, utcInstant);
  }
});

test('the same instant gives the same theme regardless of timestamp offset', () => {
  assert.deepEqual(
    { ...getSkyClock(new Date('2026-11-09T11:00:00Z')) },
    { ...getSkyClock(new Date('2026-11-09T16:30:00+05:30')) },
  );
});

test('the next update is scheduled just after the next minute', () => {
  assert.equal(msUntilNextMinute(59_999), 26);
  assert.equal(msUntilNextMinute(60_000), 60_025);
});
