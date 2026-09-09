const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

const { createImageJClient } = require('../../src/service/imageJClient');

const REPOSITORY_ROOT = path.resolve(__dirname, '../..');
const DEFAULT_MANIFEST_PATH = path.join(REPOSITORY_ROOT, 'test', 'imagej', 'fixtures', 'manifest.json');
const EXPECTED_MANIFEST_SHA256 = '1ad490afa696d3216ba566b21540086a0c91affff02c32f72107e1ce81455548';
const MEASUREMENT_FIELDS = Object.freeze(['IntDen', 'Area', 'Mean', 'Min', 'Max']);
const MEASUREMENT_TOLERANCE = 0.001;
const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const CONCURRENCY_COUNT = 20;
const CRC32_TABLE = Object.freeze(Array.from({ length: 256 }, (_unused, index) => {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) {
    value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
  }
  return value >>> 0;
}));

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value = CRC32_TABLE[(value ^ byte) & 0xff] ^ (value >>> 8);
  }
  return (value ^ 0xffffffff) >>> 0;
}

function loadManifest(manifestPath = DEFAULT_MANIFEST_PATH) {
  if (typeof manifestPath !== 'string' || manifestPath.trim().length === 0) {
    throw new TypeError('A parity manifest path is required.');
  }
  const bytes = fs.readFileSync(manifestPath);
  let manifest;
  try {
    manifest = JSON.parse(bytes.toString('utf8'));
  } catch (error) {
    throw new Error('The parity manifest is not valid JSON.', { cause: error });
  }
  if (!manifest || manifest.decodedPixelEncoding !== 'native-unfiltered-8-bit-scanlines'
      || !Array.isArray(manifest.sources) || !Array.isArray(manifest.cases)
      || manifest.cases.length === 0) {
    throw new Error('The parity manifest has an invalid structure.');
  }
  const ids = new Set();
  for (const item of manifest.cases) {
    if (!item || typeof item.id !== 'string' || !/^[a-z0-9-]+$/.test(item.id)
        || ids.has(item.id) || typeof item.operation !== 'string'
        || !item.input || typeof item.input.fixturePath !== 'string') {
      throw new Error('The parity manifest contains an invalid case.');
    }
    ids.add(item.id);
  }
  if (sha256(bytes) !== EXPECTED_MANIFEST_SHA256) {
    throw new Error('The approved parity manifest checksum does not match.');
  }
  return manifest;
}

function inspectPng(png) {
  if (!Buffer.isBuffer(png) || png.length < PNG_SIGNATURE.length
      || !png.subarray(0, PNG_SIGNATURE.length).equals(PNG_SIGNATURE)) {
    throw new Error('Expected a valid PNG buffer.');
  }
  let offset = PNG_SIGNATURE.length;
  let header;
  const compressed = [];
  let sawEnd = false;
  while (offset < png.length) {
    if (png.length - offset < 12) throw new Error('PNG chunk is truncated.');
    const length = png.readUInt32BE(offset);
    const type = png.toString('ascii', offset + 4, offset + 8);
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    const chunkEnd = dataEnd + 4;
    if (chunkEnd > png.length) throw new Error('PNG chunk exceeds the file length.');
    const data = png.subarray(dataStart, dataEnd);
    const storedCrc = png.readUInt32BE(dataEnd);
    const computedCrc = crc32(png.subarray(offset + 4, dataEnd));
    if (storedCrc !== computedCrc) throw new Error(`PNG ${type} chunk CRC is invalid.`);
    if (type === 'IHDR') {
      if (header || length !== 13) throw new Error('PNG has an invalid IHDR chunk.');
      header = {
        width: data.readUInt32BE(0),
        height: data.readUInt32BE(4),
        bitDepth: data[8],
        colorType: data[9],
        compression: data[10],
        filter: data[11],
        interlace: data[12],
      };
    } else if (type === 'IDAT') {
      compressed.push(data);
    } else if (type === 'IEND') {
      if (length !== 0 || chunkEnd !== png.length) throw new Error('PNG has an invalid IEND chunk.');
      sawEnd = true;
      break;
    }
    offset = chunkEnd;
  }
  if (!header || !sawEnd || compressed.length === 0 || header.width === 0 || header.height === 0) {
    throw new Error('PNG is missing required image chunks.');
  }
  if (header.bitDepth !== 8 || header.interlace !== 0
      || header.compression !== 0 || header.filter !== 0) {
    throw new Error('Only non-interlaced 8-bit PNGs are supported by the parity runner.');
  }
  const channels = ({ 0: 1, 2: 3, 4: 2, 6: 4 })[header.colorType];
  if (!channels) throw new Error(`Unsupported PNG color type ${header.colorType}.`);
  const stride = header.width * channels;
  let inflated;
  try {
    inflated = zlib.inflateSync(Buffer.concat(compressed));
  } catch (error) {
    throw new Error('PNG image data cannot be inflated.', { cause: error });
  }
  if (inflated.length !== header.height * (stride + 1)) {
    throw new Error('PNG decoded data length is invalid.');
  }
  const pixels = Buffer.alloc(header.height * stride);
  for (let y = 0; y < header.height; y += 1) {
    const sourceOffset = y * (stride + 1);
    const destinationOffset = y * stride;
    const filterType = inflated[sourceOffset];
    if (filterType > 4) throw new Error(`Unsupported PNG filter type ${filterType}.`);
    for (let x = 0; x < stride; x += 1) {
      const value = inflated[sourceOffset + x + 1];
      const left = x >= channels ? pixels[destinationOffset + x - channels] : 0;
      const above = y > 0 ? pixels[destinationOffset - stride + x] : 0;
      const upperLeft = y > 0 && x >= channels
        ? pixels[destinationOffset - stride + x - channels]
        : 0;
      let predictor = 0;
      if (filterType === 1) predictor = left;
      if (filterType === 2) predictor = above;
      if (filterType === 3) predictor = Math.floor((left + above) / 2);
      if (filterType === 4) predictor = paethPredictor(left, above, upperLeft);
      pixels[destinationOffset + x] = (value + predictor) & 255;
    }
  }
  return {
    width: header.width,
    height: header.height,
    bitDepth: header.bitDepth,
    colorType: header.colorType,
    decodedPixelSha256: sha256(pixels),
    fileSha256: sha256(png),
  };
}

function paethPredictor(left, above, upperLeft) {
  const prediction = left + above - upperLeft;
  const leftDistance = Math.abs(prediction - left);
  const aboveDistance = Math.abs(prediction - above);
  const upperLeftDistance = Math.abs(prediction - upperLeft);
  if (leftDistance <= aboveDistance && leftDistance <= upperLeftDistance) return left;
  return aboveDistance <= upperLeftDistance ? above : upperLeft;
}

function compareMeasurements(expected, actual) {
  if (!Array.isArray(expected) || !Array.isArray(actual) || expected.length !== actual.length) {
    return { pass: false, maxAbsoluteError: null };
  }
  let maxAbsoluteError = 0;
  for (let index = 0; index < expected.length; index += 1) {
    for (const field of MEASUREMENT_FIELDS) {
      if (!Number.isFinite(expected[index]?.[field]) || !Number.isFinite(actual[index]?.[field])) {
        return { pass: false, maxAbsoluteError: null };
      }
      maxAbsoluteError = Math.max(
        maxAbsoluteError,
        Math.abs(expected[index][field] - actual[index][field]),
      );
    }
  }
  return {
    // Decimal baseline values are serialized to three places; absorb only the
    // binary floating-point representation error around the inclusive limit.
    pass: maxAbsoluteError <= MEASUREMENT_TOLERANCE + 1e-9,
    maxAbsoluteError,
  };
}

function comparePng(expected, actual) {
  const fields = ['width', 'height', 'bitDepth', 'colorType', 'decodedPixelSha256'];
  return { pass: fields.every((field) => expected?.[field] === actual?.[field]) };
}

function validateLoopbackServiceUrl(serviceUrl) {
  if (typeof serviceUrl !== 'string' || serviceUrl.trim() !== serviceUrl || serviceUrl.length === 0) {
    throw new TypeError('A valid loopback ImageJ service URL is required.');
  }
  let parsed;
  try {
    parsed = new URL(serviceUrl);
  } catch (_error) {
    throw new TypeError('A valid loopback ImageJ service URL is required.');
  }
  const loopbackHosts = new Set(['127.0.0.1', 'localhost', '[::1]']);
  if (parsed.protocol !== 'http:' || !loopbackHosts.has(parsed.hostname)
      || parsed.username || parsed.password || !/^\/*$/.test(parsed.pathname)
      || parsed.search || parsed.hash || !parsed.port) {
    throw new TypeError('A valid loopback ImageJ service URL is required.');
  }
  return serviceUrl.replace(/\/+$/, '');
}

function resolveFixture(repositoryRoot, fixturePath) {
  const root = path.resolve(repositoryRoot);
  const resolved = path.resolve(root, fixturePath);
  if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) {
    throw new Error('A parity fixture path escapes the repository root.');
  }
  return resolved;
}

function verifySourceFixtures(manifest, repositoryRoot) {
  for (const source of manifest.sources) {
    if (!source || typeof source.fixturePath !== 'string'
        || !/^[a-f0-9]{64}$/.test(source.sourceSha256)) {
      throw new Error('The parity manifest contains an invalid source fixture entry.');
    }
    const fixture = fs.readFileSync(resolveFixture(repositoryRoot, source.fixturePath));
    if (sha256(fixture) !== source.sourceSha256) {
      throw new Error(`Parity source fixture checksum mismatch: ${source.fixturePath}`);
    }
  }
}

function operationInput(item, repositoryRoot, requestId) {
  const fixturePath = resolveFixture(repositoryRoot, item.input.fixturePath);
  const imageBuffer = fs.readFileSync(fixturePath);
  return {
    imageBuffer,
    fileName: path.basename(fixturePath),
    mimeType: 'image/png',
    options: optionsFor(item),
    requestId,
  };
}

function optionsFor(item) {
  if (item.operation === 'measure-rectangles') return { rectangles: item.input.rectangles };
  if (item.operation === 'straighten-image') return { points: item.input.points };
  if (item.operation === 'subtract-background') return { radius: item.input.radius };
  return {};
}

function invoke(client, item, input) {
  if (item.operation === 'measure-rectangles') return client.measureRectangles(input);
  if (item.operation === 'straighten-image') return client.straighten(input);
  if (item.operation === 'invert-colors') return client.invert(input);
  if (item.operation === 'convert-to-grayscale') return client.convertToGrayscale(input);
  if (item.operation === 'subtract-background') return client.subtractBackground(input);
  throw new Error(`Unsupported parity operation: ${item.operation}`);
}

async function evaluateCase({ client, item, repositoryRoot, now }) {
  const requestId = `parity-${item.id}`;
  const start = now();
  try {
    const result = await invoke(client, item, operationInput(item, repositoryRoot, requestId));
    const elapsedMs = Math.max(0, now() - start);
    if (item.operation === 'measure-rectangles') {
      const actual = result?.measurements;
      const comparison = compareMeasurements(item.measurements, actual);
      return {
        id: item.id,
        operation: item.operation,
        expected: { measurements: item.measurements },
        actual: { measurements: actual, maxAbsoluteError: comparison.maxAbsoluteError },
        elapsedMs,
        pass: comparison.pass,
      };
    }
    const actual = inspectPng(result);
    return {
      id: item.id,
      operation: item.operation,
      expected: { png: item.png },
      actual: { png: actual },
      elapsedMs,
      pass: comparePng(item.png, actual).pass,
    };
  } catch (error) {
    return {
      id: item.id,
      operation: item.operation,
      expected: item.operation === 'measure-rectangles'
        ? { measurements: item.measurements }
        : { png: item.png },
      actual: { error: safeErrorMessage(error) },
      elapsedMs: Math.max(0, now() - start),
      pass: false,
    };
  }
}

async function evaluateConcurrency({ client, item, repositoryRoot, now }) {
  const requestIds = Array.from(
    { length: CONCURRENCY_COUNT },
    (_unused, index) => `parity-concurrent-${String(index + 1).padStart(2, '0')}`,
  );
  const start = now();
  const outcomes = await Promise.all(requestIds.map(async (requestId) => {
    try {
      const result = await invoke(client, item, operationInput(item, repositoryRoot, requestId));
      if (item.operation === 'measure-rectangles') {
        return compareMeasurements(item.measurements, result?.measurements).pass;
      }
      return comparePng(item.png, inspectPng(result)).pass;
    } catch (_error) {
      return false;
    }
  }));
  return {
    caseId: item.id,
    count: CONCURRENCY_COUNT,
    requestIds,
    elapsedMs: Math.max(0, now() - start),
    pass: new Set(requestIds).size === CONCURRENCY_COUNT && outcomes.every(Boolean),
  };
}

async function runParity({
  client,
  manifestPath = DEFAULT_MANIFEST_PATH,
  repositoryRoot = REPOSITORY_ROOT,
  serviceUrl,
  token,
  timeoutMs = 30_000,
  now = Date.now,
} = {}) {
  const manifest = loadManifest(manifestPath);
  verifySourceFixtures(manifest, repositoryRoot);
  let parityClient = client;
  if (!parityClient) {
    const normalizedUrl = validateLoopbackServiceUrl(serviceUrl);
    parityClient = createImageJClient({ serviceUrl: normalizedUrl, token, timeoutMs });
  }
  validateClient(parityClient);
  const cases = [];
  for (const item of manifest.cases) {
    cases.push(await evaluateCase({ client: parityClient, item, repositoryRoot, now }));
  }
  const concurrencyCase = manifest.cases.find((item) => item.operation === 'invert-colors')
    || manifest.cases.find((item) => item.operation !== 'measure-rectangles')
    || manifest.cases[0];
  const concurrency = await evaluateConcurrency({
    client: parityClient,
    item: concurrencyCase,
    repositoryRoot,
    now,
  });
  const report = {
    schemaVersion: 1,
    manifestSha256: sha256(fs.readFileSync(manifestPath)),
    measurementTolerance: MEASUREMENT_TOLERANCE,
    cases,
    concurrency,
    pass: cases.every((item) => item.pass) && concurrency.pass,
  };
  if (!report.pass) {
    const error = new Error('ImageJ service parity verification failed.');
    error.report = report;
    throw error;
  }
  return report;
}

function validateClient(client) {
  for (const method of [
    'measureRectangles',
    'straighten',
    'invert',
    'convertToGrayscale',
    'subtractBackground',
  ]) {
    if (!client || typeof client[method] !== 'function') {
      throw new TypeError(`ImageJ parity client is missing ${method}().`);
    }
  }
}

function safeErrorMessage(error) {
  if (!error || typeof error.message !== 'string') return 'ImageJ parity operation failed.';
  const allowed = error.message.replace(/[\r\n\t]/g, ' ').slice(0, 240);
  return allowed || 'ImageJ parity operation failed.';
}

function parseCliArguments(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const name = argv[index];
    if (!['--manifest', '--service-url', '--timeout-ms'].includes(name) || index + 1 >= argv.length) {
      throw new Error(`Unknown or incomplete parity argument: ${name}`);
    }
    options[name.slice(2)] = argv[index + 1];
    index += 1;
  }
  return options;
}

async function main(argv = process.argv.slice(2), env = process.env) {
  const args = parseCliArguments(argv);
  const timeoutMs = args['timeout-ms'] === undefined ? 30_000 : Number(args['timeout-ms']);
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs < 1) {
    throw new TypeError('Parity timeout must be a positive integer in milliseconds.');
  }
  const report = await runParity({
    manifestPath: args.manifest ? path.resolve(args.manifest) : DEFAULT_MANIFEST_PATH,
    serviceUrl: args['service-url'] || env.IMAGEJ_SERVICE_URL || 'http://127.0.0.1:8200',
    token: env.IMAGEJ_SERVICE_TOKEN,
    timeoutMs,
  });
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    const output = error?.report || { pass: false, error: safeErrorMessage(error) };
    process.stderr.write(`${JSON.stringify(output, null, 2)}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  compareMeasurements,
  comparePng,
  inspectPng,
  loadManifest,
  main,
  runParity,
  validateLoopbackServiceUrl,
};
