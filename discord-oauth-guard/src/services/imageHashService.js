const sharp = require('sharp');

function hammingDistance(hashA, hashB) {
  if (!hashA || !hashB || hashA.length !== hashB.length) return Number.MAX_SAFE_INTEGER;
  let distance = 0;
  for (let index = 0; index < hashA.length; index += 1) {
    if (hashA[index] !== hashB[index]) distance += 1;
  }
  return distance;
}

class ImageHashService {
  async generateHash(filePath) {
    const { data } = await sharp(filePath, { limitInputPixels: 4096 * 4096 })
      .flatten({ background: '#ffffff' })
      .resize(8, 8, { fit: 'fill' })
      .greyscale()
      .raw()
      .toBuffer({ resolveWithObject: true });

    const pixels = [...data];
    const average = pixels.reduce((sum, pixel) => sum + pixel, 0) / pixels.length;
    return pixels.map((pixel) => (pixel >= average ? '1' : '0')).join('');
  }

  findSimilar(hash, previousHashes, maxDistance) {
    let best = null;
    for (const previous of previousHashes) {
      const distance = hammingDistance(hash, previous.hash);
      if (distance <= maxDistance && (!best || distance < best.distance)) {
        best = {
          ...previous,
          distance
        };
      }
    }
    return best;
  }

  hammingDistance(hashA, hashB) {
    return hammingDistance(hashA, hashB);
  }
}

module.exports = ImageHashService;
