const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const pool = require('../util/db');
const { SECRET_KEY, verifyToken } = require('../util/verifyToken'); // 用户验证中间件
const  { errorResponse, serverUrl } = require('../util/util');
const { straightenImage, processGrayscaleImage, subtractBackgroundFromImage, invertGrayscaleImage, measureRectangles } = require('../service');

const router = express.Router();
const upload = multer({ dest: path.join(__dirname, '../../', 'uploads/') });


/**
 * @swagger
 * /api/measure-rectangles:
 *   post:
 *     tags: [Image Processing]
 *     summary: 测量图像中的矩形框
 *     description: 根据图片上的一系列矩形框，测量每个矩形框的一些数值，包括IntDen（矩形框内像素的灰度值之和）和Area（矩形框内的像素数）、Mean（矩形框内像素的平均灰度值）、Min（矩形框内像素的最小灰度值）、Max（矩形框内像素的最大灰度值）
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               imageData:
 *                 description: The Base64 encoded image data to be measured
 *                 type: string
 *               rectangles:
 *                 description: 矩形框的数组
 *                 type: array
 *                 items:
 *                   type: object
 *                   properties:
 *                     x:
 *                       type: number
 *                     y:
 *                       type: number
 *                     width:
 *                       type: number
 *                     height:
 *                       type: number
 *     responses:
 *       200:
 *         description: 矩形框测量成功
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                 measurements:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       IntDen:
 *                         type: number
 *                       Area:
 *                         type: number
 *                       Mean:
 *                         type: number
 *                       Min:
 *                         type: number
 *                       Max:
 *                         type: number
 *       400:
 *         $ref: '#/components/responses/BadRequest'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/measure-rectangles', (req, res) => {
  // 检查请求的 JSON 体中是否包含图像数据
  const imageData = req.body.imageData;
  if (!imageData) {
    return res.status(400).send(errorResponse(400, 'missing required parameters', 'No image data provided', req));
  }
  const rectangles = req.body.rectangles; 
  if (!rectangles || rectangles.length === 0) {
    return res.status(400).send(errorResponse(400, 'missing required parameters', 'No rectangles provided', req));
  }

  // 将 Base64 数据转换为 Buffer
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
  const buffer = Buffer.from(base64Data, 'base64');
  
  // 保存原始图像为临时文件
  const imagePath = path.join(__dirname, '../../', 'uploads/', 'uploaded_image.png');

  fs.writeFile(imagePath, buffer, (err) => {
    if (err) {
      return res.status(500).send(errorResponse(500, 'Error saving image', err.message, req));
    }

    try {
      // 调用图像处理函数
      const measurements = measureRectangles(imagePath, rectangles);
      return res.send({ message: "Rectangles measured successfully", measurements });
    } catch (error) {
      return res.status(500).send(errorResponse(500, 'Error processing image', error.message, req));
    } finally {
    }
  });
});

/**
 * @swagger
 * components:
 *   schemas:
 *     Points:
 *       type: string
 *       description: A series of points to straighten the image, in JSON format
 *       example: '[{"x": 10, "y": 20}, {"x": 30, "y": 40}]'
 */

/**
 * @swagger
 * /api/straighten-image:
 *   post:
 *     tags: [Image Processing]
 *     summary: 图像拉直
 *     description: 根据图片上的一系列点（polyline），将图片拉直
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               imageData:
 *                 description: The Base64 encoded image data to be straightened
 *                 type: string
 *               points:
 *                 $ref: '#/components/schemas/Points'
 *     responses:
 *       200:
 *         description: Image straightened successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                 path:
 *                   type: string
 *       400:
 *         $ref: '#/components/responses/BadRequest'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/straighten-image', verifyToken, (req, res) => {
  // 检查请求的 JSON 体中是否包含图像数据
  const imageData = req.body.imageData;
  if (!imageData) {
    return res.status(400).send(errorResponse(400, 'missing required parameters', 'No image data provided', req));
  }
  const points = req.body.points;
  if (!points || points.length === 0) {
    return res.status(400).send(errorResponse(400, 'missing required parameters', 'No points provided', req));
  }

  // 将 Base64 数据转换为 Buffer
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
  const buffer = Buffer.from(base64Data, 'base64');
  
  // 保存原始图像为临时文件
  const imagePath = path.join(__dirname, '../../', 'uploads/', 'uploaded_image.png');
  const processedImagePath = path.join(__dirname, '../../public', 'processed', 'uploaded_image_straightened.png');

  fs.writeFile(imagePath, buffer, (err) => {
    if (err) {
      return res.status(500).send(errorResponse(500, 'Error saving image', err.message, req));
    }

    try {
      // 调用图像处理函数
      const publicImagePath = straightenImage(imagePath, points, processedImagePath);
      return res.send({ message: "Image straightened successfully", path: serverUrl(req) + publicImagePath });
    } catch (error) {
      return res.status(500).send(errorResponse(500, 'Error processing image', error.message, req));
    } finally {
    }
  });
});


/**
 * @swagger
 * /api/invert-colors:
 *   post:
 *     tags: [Image Processing]
 *     summary: 黑白图片反色
 *     description: 将黑白图片的颜色反转。图片应该使用请求体中的'imageData'字段上传。
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               imageData:
 *                 description: The Base64 encoded image data to have its colors inverted
 *                 type: string
 *     responses:
 *       200:
 *         description: Image colors inverted successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                 path:
 *                   type: string
 *       400:
 *         $ref: '#/components/responses/BadRequest'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/invert-colors', (req, res) => {
  // 检查请求的 JSON 体中是否包含图像数据
  const imageData = req.body.imageData;
  if (!imageData) {
    return res.status(400).send(errorResponse(400, 'missing required parameters', 'No image data provided', req));
  }

  // 将 Base64 数据转换为 Buffer
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
  const buffer = Buffer.from(base64Data, 'base64');
  
  // 保存原始图像为临时文件
  const imagePath = path.join(__dirname, '../../', 'uploads/', 'uploaded_image.png');
  const processedImagePath = path.join(__dirname, '../../public', 'processed', 'uploaded_image_inverted.png');

  fs.writeFile(imagePath, buffer, (err) => {
    if (err) {
      return res.status(500).send(errorResponse(500, 'Error saving image', err.message, req));
    }

    try {
      // 调用图像处理函数
      const publicImagePath = invertGrayscaleImage(imagePath, processedImagePath);
      return res.send({ message: "Image colors inverted successfully", path: serverUrl(req) + publicImagePath });
    } catch (error) {
      return res.status(500).send(errorResponse(500, 'Error processing image', error.message, req));
    } finally {
    }
  });
});

/**
 * @swagger
 * /api/convert-to-grayscale:
 *   post:
 *     tags: [Image Processing]
 *     summary: 彩色图片转为黑白
 *     description: 将彩色图片转为黑白。图片应该使用请求体中的'imageData'字段上传。
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               imageData:
 *                 description: The Base64 encoded image data to be converted to grayscale
 *                 type: string
 *     responses:
 *       200:
 *         description: Image converted to grayscale successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                 path:
 *                   type: string
 *       400:
 *         $ref: '#/components/responses/BadRequest'
 *       500:
 *         $ref: '#/components/responses/InternalServerError'
 */
router.post('/convert-to-grayscale', verifyToken, (req, res) => {
  // 检查请求的 JSON 体中是否包含图像数据
  const imageData = req.body.imageData;
  if (!imageData) {
    return res.status(400).send(errorResponse(400, 'missing required parameters', 'No image data provided', req));
  }

  // 将 Base64 数据转换为 Buffer
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
  const buffer = Buffer.from(base64Data, 'base64');

  // 保存原始图像为临时文件
  const imagePath = path.join(__dirname, '../../', 'uploads/', 'uploaded_image.png');
  const processedImagePath = path.join(__dirname, '../../public', 'processed', 'uploaded_image_grayscale.png');

  fs.writeFile(imagePath, buffer, (err) => {
    if (err) {
      return res.status(500).send(errorResponse(500, 'Error saving image', err.message, req));
    }

    try {
      // 调用图像处理函数
      const publicImagePath = processGrayscaleImage(imagePath, processedImagePath);
      return res.send({ message: "Image colors converted to grayscale successfully", path: serverUrl(req) + publicImagePath });
    } catch (error) {
      return res.status(500).send(errorResponse(500, 'Error processing image', error.message, req));
    } finally {
    }
  });
});
  
  /**
   * @swagger
   * /api/subtract-background:
   *   post:
   *     tags: [Image Processing]
   *     summary: 图像背景减除
   *     description: 对上传的图像进行背景减除。图片应该使用请求体中的'imageData'字段上传，并且需要提供减除背景的选项。
   *     requestBody:
   *       content:
   *         application/json:
   *           schema:
   *             type: object
   *             properties:
   *               imageData:
   *                 description: The Base64 encoded image data to have its background subtracted
   *                 type: string
   *               options:
   *                 type: object
   *                 properties:
   *                   radius:
   *                     type: number
   *                     description: The radius for background subtraction
   *     responses:
   *       200:
   *         description: Background subtracted successfully
   *         content:
   *           application/json:
   *             schema:
   *               type: object
   *               properties:
   *                 message:
   *                   type: string
   *                 path:
   *                   type: string
   *       400:
   *         $ref: '#/components/responses/BadRequest'
   *       500:
   *         $ref: '#/components/responses/InternalServerError'
   */
  router.post('/subtract-background', verifyToken, (req, res) => {
    const imageData = req.body.imageData;
    if (!imageData) {
      return res.status(400).send(errorResponse(400, 'missing required parameters', 'No image data provided', req));
    }
    const options = req.body.options;
    if( !options.radius || options.radius === 0) {
      return res.status(400).send(errorResponse(400, 'missing required parameters', 'No radius or radius is zero', req));
    }
  
    // 将 Base64 数据转换为 Buffer
    const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
    const buffer = Buffer.from(base64Data, 'base64');
  
    // 保存原始图像为临时文件
    const imagePath = path.join(__dirname, '../../', 'uploads/', 'uploaded_image.png');
    const processedImagePath = path.join(__dirname, '../../public', 'processed', 'uploaded_image__bg_subtracted.png');
  
    fs.writeFile(imagePath, buffer, (err) => {
      if (err) {
        return res.status(500).send(errorResponse(500, 'Error saving image', err.message, req));
      }
  
      try {
        // 调用图像处理函数
        const publicImagePath = subtractBackgroundFromImage(imagePath, processedImagePath, options.radius);
        return res.send({ message: "Background subtracted successfully", path: serverUrl(req) + publicImagePath });
      } catch (error) {
        return res.status(500).send(errorResponse(500, 'Error processing image', error.message, req));
      } finally {
      }
    });
});
  
/**
 * @swagger
 * /api/auto-detect-strips:
 *   post:
 *     tags: [Image Processing]
 *     summary: 自动识别 WB 条带坐标
 *     description: 使用 Python AI 算法自动识别图片中的条带位置并返回坐标
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               imageData:
 *                 type: string
 *                 description: Base64 编码的图像
 *     responses:
 *       200:
 *         description: 识别成功
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                 rects:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       x: { type: number }
 *                       y: { type: number }
 *                       w: { type: number }
 *                       h: { type: number }
 */
const { spawn } = require('child_process');

router.post('/auto-detect-strips', (req, res) => {
  const imageData = req.body.imageData;
  if (!imageData) {
    return res.status(400).send(errorResponse(400, 'Missing imageData', null, req));
  }

  // 准备临时文件路径
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
  const buffer = Buffer.from(base64Data, 'base64');
  const tempId = Date.now();
  const inputPath = path.join(__dirname, '../../uploads/', `detect_in_${tempId}.png`);

  // 写入临时文件供 Python 读取
  fs.writeFile(inputPath, buffer, (err) => {
    if (err) return res.status(500).send(errorResponse(500, 'Save temp image failed', err.message, req));

    // 调用 Python 脚本
    // 脚本路径建议放在专门的 scripts 目录下
    const scriptPath = path.join(__dirname, '../../scripts/wb_strip_detection.py');
    const samplesNum = req.body.samplesNum || 6; // 默认 6
    const pythonProcess = spawn('python', [
    scriptPath, 
    '--json_mode', 
    '--file', inputPath,
    '--samples', samplesNum.toString() // 传入样本数
    ]);

    let resultData = '';
    let errorData = '';

    pythonProcess.stdout.on('data', (data) => {
      resultData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorData += data.toString();
    });

    pythonProcess.on('close', (code) => {
      // 清理临时文件

      if (fs.existsSync(inputPath)) {
        fs.unlink(inputPath, (unlinkErr) => {
            if (unlinkErr) {
                console.error(`[清理失败] 无法删除临时文件: ${inputPath}`, unlinkErr);
            } else {
                // 如果定义了 tempFileName 就用它，否则用 inputPath
                console.log(`[清理成功] 临时文件已移除`);
            }
        });
     }

      if (code !== 0) {
        console.error('Python 进程退出异常，退出码:', code);
        console.error('错误输出:', errorData);
        return res.status(500).send(errorResponse(500, 'Algorithm Error', errorData, req));
    }

      try {
        const rects = JSON.parse(resultData);
        return res.send({ success: true, rects });
      } catch (e) {
        console.error('解析 Python 输出失败:', e.message);
        return res.status(500).send(errorResponse(500, 'Parse output failed', e.message, req));
      }
    });
  });
});

module.exports = router;