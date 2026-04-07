const path = require('path');
const fs = require('fs');
const java = require('java');

java.classpath.push(path.join(__dirname, 'ij.jar'));
java.options.push('-Xmx1500m');
java.options.push('-Djava.awt.headless=true');


function roundTo(num) {
  return parseFloat(num.toFixed(3)); // 或者使用 Number(num.toFixed(3))
}

const measureRectangles = (imagePath, rectangles) => {
  const Options = {
    AREA: 1,
    MEAN: 2,
    STD_DEV: 4,
    MODE: 8,
    MIN_MAX: 16,
    CENTROID: 32,
    CENTER_OF_MASS: 64,
    PERIMETER: 128,
    LIMIT: 256,
    RECT: 512,
    LABELS: 1024,
    ELLIPSE: 2048,
    INVERT_Y: 4096,
    CIRCULARITY: 8192,
    SHAPE_DESCRIPTORS: 8192,
    FERET: 16384,
    INTEGRATED_DENSITY: 0x8000,
    MEDIAN: 0x10000,
    SKEWNESS: 0x20000,
    KURTOSIS: 0x40000,
    AREA_FRACTION: 0x80000,
    SLICE: 0x100000,
    STACK_POSITION: 0x100000,
    SCIENTIFIC_NOTATION: 0x200000,
    ADD_TO_OVERLAY: 0x400000,
    NaN_EMPTY_CELLS: 0x800000
  };

  try {
    const ImagePlus = java.import('ij.ImagePlus');
    const imgPlus = new ImagePlus(imagePath);

    if (!imgPlus) {
      throw new Error("Image could not be opened. Check the image file.");
    }

    const measurements = [];
    //const RoiManager = java.import('ij.plugin.frame.RoiManager');
    //const roiManager = new RoiManager();

    rectangles.forEach(rect => {
      const { x, y, width, height } = rect;
      const Roi = java.import('ij.gui.Roi');
      const roi = new Roi(x, y, width, height);
      //roiManager.addRoiSync(roi);

      imgPlus.setRoiSync(roi);

      //roiManager.runCommandSync('Measure');

      const stats = imgPlus.getStatisticsSync(Options.AREA|Options.MEAN|Options.MIN_MAX|Options.INTEGRATED_DENSITY);
      measurements.push({
        IntDen: roundTo(stats.area * stats.mean),
        Area: roundTo(stats.area),
        Mean: roundTo(stats.mean),
        Min: roundTo(stats.min),
        Max: roundTo(stats.max)
      });
      imgPlus.deleteRoiSync();
    });

    return measurements;
  } catch (error) {
    console.error('Error measuring rectangles:', error);
    throw error;
  } finally {
    fs.unlinkSync(imagePath);
  }
};

const straightenImage = (imagePath, points, processedImagePath) => {
  try {
    const ImagePlus = java.import('ij.ImagePlus');
    const imgPlus = new ImagePlus(imagePath);

    if (!imgPlus) {
      throw new Error("Image could not be opened. Check the image file.");
    }

    console.log('points=:', points);
    // 解析 points 字符串为 JSON 对象
    const parsedPoints = JSON.parse(points);
    
    //return;
    /*const PolygonRoi = java.import('ij.gui.PolygonRoi');
    let b = parsedPoints.map(point => point.y); //, parsedPoints.map(point => point.y), parsedPoints.length, 6;
    const polyline = new PolygonRoi(parsedPoints.map(point => parseFloat(point.x)), parsedPoints.map(point => parseFloat(point.y)), parsedPoints.length, 6);*/
    //const Point = java.import('java.awt.Point');
    //const polyline = points.map(point => new Point(point.x, point.y));

    // 确保导入正确的Java类
    const PolygonRoi = java.import('ij.gui.PolygonRoi');

    // 转换 parsedPoints 中的坐标为 float 数组
    const xPoints = parsedPoints.map(point => parseFloat(point.x));
    const yPoints = parsedPoints.map(point => parseFloat(point.y));

    // 使用 PolygonRoi 的构造函数
    const polyline = new PolygonRoi(
      java.newArray('float', xPoints),  // 确保传递 float[]
      java.newArray('float', yPoints),  // 确保传递 float[]
      parsedPoints.length,           // 点个数
      6                              // 6 代表了类型，如多边形
    );


    imgPlus.setRoiSync(polyline);
    const Straightener = java.import('ij.plugin.Straightener');
    const straightener = new Straightener();
    const ImageProcessor2 = straightener.straightenSync(imgPlus, polyline, 100);
    //const test = straightener.straightenCompositeSync(imgPlus, polyline, 40);

    const processedDir = path.join(__dirname, '../public', 'processed');
    if (!fs.existsSync(processedDir)) {
      fs.mkdirSync(processedDir);
    }

    const imgPlus2 = new ImagePlus('c', ImageProcessor2);
    const FileSaver = java.import('ij.io.FileSaver');
    const fileSaver = new FileSaver(imgPlus2);
    fileSaver.saveAsPngSync(processedImagePath);

    return '/' + 'processed/' + path.basename(processedImagePath);
  } catch (error) {
    console.error('Error straightening image:', error);
    throw error;
  } finally {
    fs.unlinkSync(imagePath);
  }
};

// invert a grayscale image
const invertGrayscaleImage = (imagePath, processedImagePath) => {
  try {
    const ImagePlus = java.import('ij.ImagePlus');
    const imgPlus = new ImagePlus(imagePath);

    if (!imgPlus) {
      throw new Error("Image could not be opened. Check the image file.");
    }

    imgPlus.getProcessorSync().invertSync();
    imgPlus.updateAndDrawSync();

    const processedDir = path.join(__dirname, '../public', 'processed');
    if (!fs.existsSync(processedDir)) {
      fs.mkdirSync(processedDir);
    }

    const FileSaver = java.import('ij.io.FileSaver');
    const fileSaver = new FileSaver(imgPlus);
    fileSaver.saveAsPngSync(processedImagePath);

    return '/' + 'processed/' + path.basename(processedImagePath);
  } catch (error) {
    console.error('Error processing image:', error);
    throw error;
  } finally {
    fs.unlinkSync(imagePath);
  }
};

const processGrayscaleImage = (imagePath, processedImagePath) => {
  try {
    const ImagePlus = java.import('ij.ImagePlus');
    const imgPlus = new ImagePlus(imagePath);

    if (!imgPlus) {
      throw new Error("Image could not be opened. Check the image file.");
    }

    const GrayscaleConverter = java.import('ij.process.ImageConverter');
    const converter = new GrayscaleConverter(imgPlus);
    converter.convertToGray8Sync();

    imgPlus.updateAndDrawSync();

    const processedDir = path.join(__dirname, '../public', 'processed');
    if (!fs.existsSync(processedDir)) {
      fs.mkdirSync(processedDir);
    }

    const FileSaver = java.import('ij.io.FileSaver');
    const fileSaver = new FileSaver(imgPlus);
    fileSaver.saveAsPngSync(processedImagePath);

    return '/' + 'processed/' + path.basename(processedImagePath);
  } catch (error) {
    console.error('Error processing image:', error);
    throw error;
  } finally {
    fs.unlinkSync(imagePath);
  }
};

const subtractBackgroundFromImage = (imagePath, processedImagePath, radius) => {
  try {
    const ImagePlus = java.import('ij.ImagePlus');
    const imgPlus = new ImagePlus(imagePath);

    if (!imgPlus) {
      throw new Error("Image could not be opened. Check the image file.");
    }

    const BackgroundSubtractor = java.import('ij.plugin.filter.BackgroundSubtracter');
    const backgroundSubtractor = new BackgroundSubtractor();
    //backgroundSubtractor.subtractRGBBackroundSync(imgPlus.getProcessorSync(), 50);
    backgroundSubtractor.subtractBackroundSync(imgPlus.getProcessorSync(), radius);

    imgPlus.updateAndDrawSync();

    const processedDir = path.join(__dirname, '../public', 'processed');
    if (!fs.existsSync(processedDir)) {
      fs.mkdirSync(processedDir);
    }

    const FileSaver = java.import('ij.io.FileSaver');
    const fileSaver = new FileSaver(imgPlus);
    fileSaver.saveAsPngSync(processedImagePath);

    return '/' + 'processed/' + path.basename(processedImagePath);
  } catch (error) {
    console.error('Error processing image:', error);
    throw error;
  } finally {
    fs.unlinkSync(imagePath);
  }
};
module.exports = {
  measureRectangles,
  straightenImage,
  invertGrayscaleImage,
  processGrayscaleImage,
  subtractBackgroundFromImage
};