"""
WB条带黑条识别脚本
识别PNG图片中的黑色条带并去除背景干扰
"""
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import List, Tuple, Optional
from scipy import ndimage
import os
import argparse
import sys


class WBStripDetector:
    """WB条带检测器"""

    def __init__(self, input_dir: str = None, output_dir: str = None):
        """
        初始化检测器

        参数:
            input_dir: 输入目录路径（如果为None，则使用命令行参数或默认值）
            output_dir: 输出目录路径（如果为None，则自动生成）
        """
        if input_dir:
            self.input_dir = Path(input_dir)
        else:
            # 默认使用用户指定的路径
            self.input_dir = Path(r"D:\all\wb\test")

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # 自动生成输出目录：在输入目录名后加_annotated
            self.output_dir = Path(str(self.input_dir) + "_annotated")

    def blackhat_transform(self, image: np.ndarray, kernel_width: int = 100, kernel_height: int = 5) -> np.ndarray:
        """
        黑帽运算（Black Hat）：闭运算结果减去原图
        用于从灰色背景中凸显黑条

        参数:
            image: 灰度图
            kernel_width: 横向核宽度（应该大一点）
            kernel_height: 纵向核高度（略高于条带高度）

        返回:
            黑帽运算后的图像
        """
        # 确保核大小为奇数
        if kernel_width % 2 == 0:
            kernel_width += 1
        if kernel_height % 2 == 0:
            kernel_height += 1

        # 创建水平方向的结构元素
        structure = np.ones((kernel_height, kernel_width), dtype=np.uint8)

        # 闭运算：先膨胀后腐蚀（填充条带内部的小孔）
        closed = ndimage.grey_closing(image, structure=structure)

        # 黑帽：闭运算结果减去原图（突出比周围暗的区域）
        blackhat = closed.astype(np.float32) - image.astype(np.float32)

        # 归一化到0-255
        blackhat = np.clip(blackhat, 0, 255).astype(np.uint8)

        return blackhat

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        """
        去除背景干扰，增强条带对比度

        参数:
            image: 灰度图

        返回:
            去除背景后的图像
        """
        # 使用滚动球算法（Rolling Ball）的思想去除背景
        # 使用形态学操作估计背景，然后减去

        # 计算合适的结构元素大小
        structure_width = max(20, min(image.shape[1] // 10, 100))
        structure_height = 5  # 垂直方向稍大，以更好地估计背景

        # 创建水平方向的结构元素
        structure = np.ones((structure_height, structure_width), dtype=np.uint8)

        # 形态学开运算估计背景（去除条带等细节，保留背景）
        background = ndimage.grey_opening(image, structure=structure)
        # 形态学闭运算平滑背景
        background = ndimage.grey_closing(background, structure=structure)

        # 减去背景（保留条带）
        result = image.astype(np.float32) - background.astype(np.float32)

        # 只保留正值（暗条带）
        result = np.maximum(result, 0)

        # 归一化并增强对比度
        if result.max() > 0:
            result = (result / result.max() * 255).astype(np.uint8)
        else:
            result = image.copy()  # 如果背景去除失败，使用原图

        # 对比度增强（使用更温和的方法）
        result = self.enhance_contrast(result)

        return result

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        增强对比度

        参数:
            image: 灰度图

        返回:
            对比度增强后的图像
        """
        # 线性拉伸（使用适中的百分位数范围）
        p5, p95 = np.percentile(image, (5, 95))
        if p95 > p5:
            enhanced = ((image.astype(np.float32) - p5) / (p95 - p5) * 255).astype(np.uint8)
            enhanced = np.clip(enhanced, 0, 255)
        else:
            enhanced = image.copy()

        # 使用gamma校正增强暗部（使用更温和的gamma值）
        gamma = 0.8  # 稍微增强暗部，不要太激进
        enhanced = np.power(enhanced.astype(np.float32) / 255.0, gamma) * 255.0
        enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)

        return enhanced

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        预处理图像：转换为灰度图、去除背景、去噪

        参数:
            image: 输入图像（RGB格式或灰度）

        返回:
            预处理后的灰度图
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            # RGB转灰度: 使用加权平均
            gray = np.dot(image[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
        else:
            gray = image.copy()

        # 轻微去噪
        gray = ndimage.gaussian_filter(gray, sigma=1.0)

        # 去除背景（使用更温和的方法）
        gray = self.remove_background(gray)

        return gray

    def adaptive_threshold(self, image: np.ndarray, block_size: int = 51, C: float = 10.0) -> np.ndarray:
        """
        自适应阈值处理，更好地处理不均匀光照和背景干扰

        参数:
            image: 灰度图
            block_size: 局部区域大小（必须是奇数）
            C: 阈值调整常数
                如果C>0: 检测暗区域 (image < local_mean - C)
                如果C<0: 检测亮区域 (image > local_mean - C)

        返回:
            二值化图像
        """
        # 确保block_size是奇数
        if block_size % 2 == 0:
            block_size += 1

        # 计算局部均值
        local_mean = ndimage.uniform_filter(image.astype(np.float32), size=block_size)

        # 自适应阈值
        if C > 0:
            # 检测暗区域（原黑条）
            binary = (image < (local_mean - C)).astype(np.uint8) * 255
        else:
            # 检测亮区域（黑帽后的高亮条）
            binary = (image > (local_mean - C)).astype(np.uint8) * 255

        return binary

    def remove_background_noise(self, binary: np.ndarray, min_area: int = 50) -> np.ndarray:
        """
        去除小的背景噪声

        参数:
            binary: 二值图像
            min_area: 最小保留区域面积

        返回:
            清理后的二值图像
        """
        # 查找连通组件
        labeled, num_features = ndimage.label(binary > 127)

        # 计算每个组件的面积
        sizes = ndimage.sum(binary > 127, labeled, range(1, num_features + 1))

        # 创建掩码，只保留面积大于阈值的组件
        mask = np.zeros_like(binary, dtype=bool)
        for i in range(1, num_features + 1):
            if sizes[i-1] >= min_area:
                mask[labeled == i] = True

        return (mask * 255).astype(np.uint8)

    def morphological_cleanup(self, binary: np.ndarray) -> np.ndarray:
        """
        形态学操作清理图像

        参数:
            binary: 二值图像

        返回:
            清理后的二值图像
        """
        # 水平方向的核（用于连接条带中的断裂）
        horizontal_kernel = np.ones((1, 15), dtype=np.uint8)

        # 垂直方向的核（用于去除垂直方向的干扰）
        vertical_kernel = np.ones((5, 1), dtype=np.uint8)

        # 先进行水平方向的闭运算（连接断裂的条带）
        dilated_h = ndimage.binary_dilation(binary > 127, structure=horizontal_kernel, iterations=2)
        closed_h = ndimage.binary_erosion(dilated_h, structure=horizontal_kernel, iterations=2)

        # 再进行垂直方向的开运算（去除垂直方向的干扰）
        eroded_v = ndimage.binary_erosion(closed_h, structure=vertical_kernel, iterations=1)
        opened_v = ndimage.binary_dilation(eroded_v, structure=vertical_kernel, iterations=1)

        return (opened_v * 255).astype(np.uint8)

    def filter_same_level_strips(self, strips: List[dict], image_height: int) -> List[dict]:
        """
        筛选同一水平线上的条带，并过滤尺寸相似的条带

        参数:
            strips: 条带列表，每个条带是字典 {'x', 'y', 'width', 'height', 'center_y', 'area'}
            image_height: 图像高度

        返回:
            筛选后的条带列表
        """
        if len(strips) == 0:
            return []

        # 按中心y坐标分组（允许一定误差）
        tolerance = max(5, image_height // 50)  # y坐标容差

        # 找到最密集的水平线（包含最多条带）
        y_coords = [s['center_y'] for s in strips]
        best_level = None
        max_count = 0

        for y in y_coords:
            # 统计在这个y坐标附近的条带数量
            count = sum(1 for s in strips if abs(s['center_y'] - y) <= tolerance)
            if count > max_count:
                max_count = count
                best_level = y

        if best_level is None:
            return []

        # 筛选同一水平线上的条带
        same_level_strips = [s for s in strips if abs(s['center_y'] - best_level) <= tolerance]

        # 如果条带数量较多，进一步筛选：尺寸相似性
        if len(same_level_strips) > 5:
            # 计算宽度和高度的中位数
            widths = [s['width'] for s in same_level_strips]
            heights = [s['height'] for s in same_level_strips]
            median_width = np.median(widths)
            median_height = np.median(heights)

            # 筛选尺寸接近中位数的条带（允许30%的偏差）
            filtered = []
            for s in same_level_strips:
                width_ratio = s['width'] / median_width if median_width > 0 else 1
                height_ratio = s['height'] / median_height if median_height > 0 else 1

                # 宽度和高度都应该在合理范围内（0.5-2.0倍）
                if 0.5 <= width_ratio <= 2.0 and 0.5 <= height_ratio <= 2.0:
                    filtered.append(s)

            # 如果筛选后还有较多条带，选择面积最大的几个
            if len(filtered) > 10:
                filtered.sort(key=lambda s: s['area'], reverse=True)
                filtered = filtered[:10]  # 最多保留10个

            return filtered

        return same_level_strips

    def detect_strips_from_binary(self, binary: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        从二值图像中检测条带并提取中点

        参数:
            binary: 二值图像

        返回:
            检测到的条带列表，每个条带为 (x, y, width, height)
        """
        labeled, num_features = ndimage.label(binary > 127)
        strips = []

        min_aspect_ratio = 1.5
        max_aspect_ratio = 50.0
        min_area = max(50, binary.size // 10000)
       

        for i in range(1, num_features + 1):
            mask = labeled == i
            coords = np.where(mask)

            if len(coords[0]) == 0:
                continue

            y_min, y_max = coords[0].min(), coords[0].max()
            x_min, x_max = coords[1].min(), coords[1].max()
            width = x_max - x_min + 1
            height = y_max - y_min + 1
            area = mask.sum()
            aspect_ratio = width / height if height > 0 else 0

            # 筛选条件
            if aspect_ratio >= min_aspect_ratio and aspect_ratio <= max_aspect_ratio and area >= min_area:
                strips.append((x_min, y_min, width, height))

        # 按y坐标排序
        strips.sort(key=lambda s: s[1])

        return strips

    def detect_strips_by_projection(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        使用行投影方法检测条带（更稳健的方法）

        参数:
            image: 预处理后的灰度图

        返回:
            检测到的条带列表
        """
        # 计算每行的平均亮度
        row_means = image.mean(axis=1)
        row_std = np.std(row_means)
        row_median = np.median(row_means)
        row_mean = np.mean(row_means)

        # 计算阈值：使用中位数减去一定倍数的标准差
        threshold = row_median - row_std * 1.2

        # 找到暗行
        dark_rows = row_means < threshold

        # 找到连续暗行区域
        strips = []
        in_strip = False
        strip_start = 0

        for y in range(len(dark_rows)):
            if dark_rows[y] and not in_strip:
                strip_start = y
                in_strip = True
            elif not dark_rows[y] and in_strip:
                strip_height = y - strip_start
                if strip_height >= 2:  # 至少2行
                    # 计算条带的左右边界（在暗行区域内）
                    strip_region = image[strip_start:y, :]
                    # 计算每列的平均亮度
                    col_means = strip_region.mean(axis=0)
                    col_threshold = col_means.mean() - col_means.std() * 0.5
                    dark_cols = col_means < col_threshold

                    # 找到连续暗列区域
                    if dark_cols.any():
                        col_start = np.where(dark_cols)[0][0]
                        col_end = np.where(dark_cols)[0][-1] + 1
                        width = col_end - col_start

                        if width >= 10:  # 至少10像素宽
                            strips.append((col_start, strip_start, width, strip_height))
                in_strip = False

        # 处理最后一个条带
        if in_strip:
            strip_height = len(dark_rows) - strip_start
            if strip_height >= 2:
                strip_region = image[strip_start:, :]
                col_means = strip_region.mean(axis=0)
                col_threshold = col_means.mean() - col_means.std() * 0.5
                dark_cols = col_means < col_threshold
                if dark_cols.any():
                    col_start = np.where(dark_cols)[0][0]
                    col_end = np.where(dark_cols)[0][-1] + 1
                    width = col_end - col_start
                    if width >= 10:
                        strips.append((col_start, strip_start, width, strip_height))

        return strips

    def detect_dark_strips(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        检测图像中的黑色条带

        参数:
            image: 预处理后的灰度图

        返回:
            检测到的条带列表，每个条带为 (x, y, width, height)
        """
        image_mean = np.mean(image)
        image_std = np.std(image)
        image_median = np.median(image)

        # 更智能的参数调整（背景去除后，图像对比度增强）
        # 注意：背景去除后，图像均值可能会变化，需要重新评估
        if image_mean > 180:
            # 高亮度背景
            adaptive_C = max(4.0, image_mean * 0.04)
            brightness_threshold = min(image_mean * 0.88, image_median * 0.85)
            contrast_threshold = 0.90  # 背景去除后，条带对比度更明显
        elif image_mean > 100:
            # 中等亮度
            adaptive_C = 6.0
            brightness_threshold = image_mean * 0.82
            contrast_threshold = 0.88
        else:
            # 较暗的图像
            adaptive_C = 8.0
            brightness_threshold = image_mean * 0.75
            contrast_threshold = 0.85

        # 方法1: 自适应阈值（背景去除后，可以使用较小的block_size）
        binary1 = self.adaptive_threshold(image, block_size=51, C=adaptive_C)

        # 方法2: OTSU阈值（作为补充）
        hist, bins = np.histogram(image.flatten(), 256, [0, 256])
        hist_norm = hist.astype(np.float32) / hist.sum()
        cumsum = np.cumsum(hist_norm)
        cummean = np.cumsum(hist_norm * np.arange(256))
        global_mean = cummean[-1]

        between_class_variance = np.zeros(256)
        for t in range(256):
            w0 = cumsum[t]
            w1 = 1 - w0
            if w0 == 0 or w1 == 0:
                continue
            m0 = cummean[t] / w0 if w0 > 0 else 0
            m1 = (global_mean - cummean[t]) / w1 if w1 > 0 else 0
            between_class_variance[t] = w0 * w1 * (m0 - m1) ** 2

        otsu_threshold = np.argmax(between_class_variance)
        binary2 = (image < otsu_threshold).astype(np.uint8) * 255

        # 方法3: 改进的行平均检测（只标记连续暗行区域，而不是整行）
        row_means = image.mean(axis=1)
        row_median = np.median(row_means)
        row_mean = np.mean(row_means)
        row_std = np.std(row_means)
        # 使用适中的阈值：均值减去1.2倍标准差，或中位数减去1.5倍标准差，取较小值
        row_threshold1 = row_mean - row_std * 1.2
        row_threshold2 = row_median - row_std * 1.5
        row_threshold = min(row_threshold1, row_threshold2)

        # 找到连续暗行区域
        dark_rows = row_means < row_threshold
        binary3 = np.zeros_like(image, dtype=np.uint8)

        # 只标记连续暗行区域（至少2行连续，降低要求）
        in_dark_region = False
        dark_start = 0
        for y in range(len(dark_rows)):
            if dark_rows[y] and not in_dark_region:
                dark_start = y
                in_dark_region = True
            elif not dark_rows[y] and in_dark_region:
                if y - dark_start >= 2:  # 至少2行连续
                    binary3[dark_start:y, :] = 255
                in_dark_region = False
        if in_dark_region and len(dark_rows) - dark_start >= 2:
            binary3[dark_start:, :] = 255

        # 合并三种方法的结果（使用OR操作）
        binary = np.maximum(np.maximum(binary1, binary2), binary3)

        # 去除背景噪声（根据图像大小调整最小面积，降低要求）
        min_area = max(30, image.size // 8000)  # 降低最小面积要求
       
        binary = self.remove_background_noise(binary, min_area=int(min_area))

        # 形态学清理（使用更温和的操作）
        binary = self.morphological_cleanup(binary)

        # 方法4: 使用行投影方法（更稳健）
        projection_strips = self.detect_strips_by_projection(image)

        # 查找连通组件
        labeled, num_features = ndimage.label(binary > 127)

        strips = []

        for i in range(1, num_features + 1):
            mask = labeled == i
            coords = np.where(mask)

            if len(coords[0]) == 0:
                continue

            y_min, y_max = coords[0].min(), coords[0].max()
            x_min, x_max = coords[1].min(), coords[1].max()

            width = x_max - x_min + 1
            height = y_max - y_min + 1
            area = mask.sum()
            aspect_ratio = width / height if height > 0 else 0

            # 过滤条件：条带应该是横向的（宽度大于高度）
            # 放宽长宽比限制，允许更短的条带
            if aspect_ratio < 1.2 or aspect_ratio > 200.0:  # 进一步放宽最小长宽比
                continue

            # 检查尺寸（根据图像大小动态调整，放宽限制）
            img_width, img_height = image.shape[1], image.shape[0]
            min_width = max(10, img_width // 50)  # 降低最小宽度要求（至少是图像宽度的1/50）
            max_width = min(3000, img_width * 2)   # 最多是图像宽度的2倍
            min_height = max(2, img_height // 300)  # 降低最小高度要求（至少是图像高度的1/300）
            max_height = min(300, img_height // 2)   # 最多是图像高度的一半

            if width < min_width or width > max_width:
                continue
            if height < min_height or height > max_height:
                continue

            # 检查区域的平均亮度（确保是暗色条带）
            roi = image[y_min:y_max+1, x_min:x_max+1]
            roi_mean = np.mean(roi)

            # 条带应该比整体图像暗（使用动态阈值）
            if roi_mean > brightness_threshold:
                continue

            # 检查对比度（条带应该比周围区域暗）
            # 使用更大的margin来获取更准确的周围区域
            margin = max(10, min(20, max(height, width) // 5))
            x1 = max(0, x_min - margin)
            y1 = max(0, y_min - margin)
            x2 = min(image.shape[1], x_max + margin + 1)
            y2 = min(image.shape[0], y_max + margin + 1)

            # 计算周围区域（排除条带本身）
            surrounding_mask = np.ones((y2 - y1, x2 - x1), dtype=bool)
            local_y_min = y_min - y1
            local_y_max = y_max - y1 + 1
            local_x_min = x_min - x1
            local_x_max = x_max - x1 + 1
            surrounding_mask[local_y_min:local_y_max, local_x_min:local_x_max] = False

            surrounding_region = image[y1:y2, x1:x2]
            surrounding_mean = np.mean(surrounding_region[surrounding_mask]) if surrounding_mask.sum() > 0 else image_mean

            # 条带应该比周围暗（使用动态对比度阈值）
            if roi_mean > surrounding_mean * contrast_threshold:
                continue

            # 额外检查：条带的亮度变化应该较小（条带内部应该相对均匀）
            # 条带的标准差应该小于周围区域的标准差
            roi_std = np.std(roi)
            surrounding_std = np.std(surrounding_region[surrounding_mask]) if surrounding_mask.sum() > 0 else image_std
            # 进一步放宽条件：背景去除后，条带内部可能有一些变化
            if roi_std > surrounding_std * 2.5:
                continue

            # 检查条带的填充度（条带区域中暗像素的比例）
            # 条带区域中应该有足够比例的暗像素
            # 背景去除后，条带会更明显，但阈值可能需要调整
            dark_pixel_ratio = (roi < brightness_threshold).sum() / roi.size
            # 使用更宽松的阈值，因为背景去除后对比度增强
            if dark_pixel_ratio < 0.20:  # 至少20%的像素应该是暗的
                continue
            roi_std = np.std(roi)
            if roi_std > image_std * 1.5:  # 条带内部变化不应该太大
                continue

            strips.append((x_min, y_min, width, height))

        # 合并投影方法检测到的条带
        # 去重：如果两个条带重叠度很高，只保留一个
        all_strips = strips + projection_strips
        if len(all_strips) > 0:
            # 按y坐标排序
            all_strips.sort(key=lambda s: s[1])

            # 去重：合并重叠的条带
            merged_strips = []
            for strip in all_strips:
                x, y, w, h = strip
                merged = False
                for i, existing in enumerate(merged_strips):
                    ex, ey, ew, eh = existing
                    # 检查重叠度
                    overlap_y = max(0, min(y + h, ey + eh) - max(y, ey))
                    overlap_x = max(0, min(x + w, ex + ew) - max(x, ex))
                    overlap_area = overlap_y * overlap_x
                    min_area_strip = min(w * h, ew * eh)

                    if overlap_area > min_area_strip * 0.5:  # 重叠度超过50%
                        # 合并条带
                        new_x = min(x, ex)
                        new_y = min(y, ey)
                        new_w = max(x + w, ex + ew) - new_x
                        new_h = max(y + h, ey + eh) - new_y
                        merged_strips[i] = (new_x, new_y, new_w, new_h)
                        merged = True
                        break

                if not merged:
                    merged_strips.append(strip)

            strips = merged_strips

        # 按y坐标排序（从上到下）
        strips.sort(key=lambda s: s[1])

        return strips

    def annotate_image(self, image: Image.Image, strips: List[Tuple[int, int, int, int]]) -> Image.Image:
        """
        在图像上标注检测到的条带

        参数:
            image: PIL图像对象
            strips: 检测到的条带列表

        返回:
            标注后的图像
        """
        annotated = image.copy()

        # 如果是灰度图，转换为RGB以便绘制彩色标注
        if annotated.mode in ('L', 'LA', 'P', '1'):
            annotated = annotated.convert('RGB')

        draw = ImageDraw.Draw(annotated)

        # 尝试加载字体
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)  # 微软雅黑
            except:
                font = ImageFont.load_default()

        for i, (x, y, w, h) in enumerate(strips):
            # 计算中点
            center_x = x + w // 2
            center_y = y + h // 2

            # 绘制矩形框（红色，宽度2）
            draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=2)

            # 绘制中心点（蓝色圆点）
            draw.ellipse([center_x - 5, center_y - 5, center_x + 5, center_y + 5],
                        fill=(0, 0, 255))

        return annotated

    def save_debug_images(self, image_path: Path, steps: dict, relative_path: Path = None):
        """
        保存调试图像（每一步的处理结果）

        参数:
            image_path: 原始图像路径
            steps: 字典，包含每一步的处理结果 {'step_name': image_array}
            relative_path: 相对路径（用于保持目录结构）
        """
        debug_dir = self.output_dir / "debug"
        if relative_path:
            debug_dir = debug_dir / relative_path.parent
        debug_dir.mkdir(parents=True, exist_ok=True)

        for step_name, step_image in steps.items():
            if step_image is not None:
                if len(step_image.shape) == 2:
                    # 灰度图
                    debug_img = Image.fromarray(step_image, mode='L')
                else:
                    # RGB图
                    debug_img = Image.fromarray(step_image)

                debug_path = debug_dir / f"{image_path.stem}_{step_name}.png"
                debug_img.save(str(debug_path))

    def process_image(self, image_path: Path, relative_path: Path = None, debug: bool = False) -> Tuple[bool, int]:
        """
        处理单张图片

        参数:
            image_path: 输入图片路径（绝对路径）
            relative_path: 相对于输入目录的路径（用于保持输出目录结构）

        返回:
            (是否成功, 检测到的条带数量)
        """
        try:
            # 读取图像
            pil_image = Image.open(str(image_path))
            image_array = np.array(pil_image)

            print(f"\n处理: {image_path.name}")
            print(f"  图像尺寸: {image_array.shape[1]}x{image_array.shape[0]}")

            # 保存调试图像的字典
            debug_steps = {}
            if debug:
                debug_steps['00_original'] = image_array

            # 步骤1: 转为灰度（如果已经是灰度图则直接使用）
            if len(image_array.shape) == 3:
                gray = np.dot(image_array[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
            else:
                gray = image_array.copy()

            if debug:
                debug_steps['01_gray'] = gray

            # 步骤2: 高斯模糊去噪
            gaussian_blurred = ndimage.gaussian_filter(gray, sigma=1.5)
            if debug:
                debug_steps['02_gaussian_blur'] = gaussian_blurred

            # 步骤3: 中值滤波去噪（去除轻微噪点）
            median_filtered = ndimage.median_filter(gaussian_blurred, size=3)
            if debug:
                debug_steps['03_median_filter'] = median_filtered

            # 步骤4: 黑帽运算（从灰色背景中凸显黑条）
            # 根据图像大小动态调整核大小
            img_width = median_filtered.shape[1]
            kernel_width = max(50, min(img_width // 8, 150))  # 横向核大一点
            kernel_height = 5  # 纵向略高于条带高度（约3-4像素）
            blackhat = self.blackhat_transform(median_filtered, kernel_width=kernel_width, kernel_height=kernel_height)
            if debug:
                debug_steps['04_blackhat'] = blackhat

            # 步骤5: 对比度增强（使用非常温和的方法，保留黑条特征）
            # 黑帽运算后，黑条已经变成高亮条，只需要轻微增强对比度
            # 方法：简单的线性拉伸，使用较宽的百分位数范围，避免过度增强
            p5, p95 = np.percentile(blackhat, (5, 95))
            if p95 > p5 and p95 > 0:
                # 只拉伸到255的80%，避免过度增强
                max_val = min(255, p95 * 1.2)
                stretched = ((blackhat.astype(np.float32) - p5) / (p95 - p5) * max_val).astype(np.uint8)
                stretched = np.clip(stretched, 0, 255)
            else:
                stretched = blackhat.copy()

            if debug:
                debug_steps['05_contrast_enhancement'] = stretched

            # 步骤6: 自适应阈值二值化（直接在黑帽结果上处理，黑条已经是高亮的）
            # 对于黑帽结果，高亮区域（原黑条）应该用正向阈值检测
            # 使用OTSU阈值作为主要方法，更稳健
            hist, bins = np.histogram(stretched.flatten(), 256, [0, 256])
            hist_norm = hist.astype(np.float32) / hist.sum()
            cumsum = np.cumsum(hist_norm)
            cummean = np.cumsum(hist_norm * np.arange(256))
            global_mean = cummean[-1]
            between_class_variance = np.zeros(256)
            for t in range(256):
                w0 = cumsum[t]
                w1 = 1 - w0
                if w0 == 0 or w1 == 0:
                    continue
                m0 = cummean[t] / w0 if w0 > 0 else 0
                m1 = (global_mean - cummean[t]) / w1 if w1 > 0 else 0
                between_class_variance[t] = w0 * w1 * (m0 - m1) ** 2
            otsu_threshold = np.argmax(between_class_variance)
            # 对于黑帽结果，高亮区域（原黑条）应该大于阈值
            otsu_binary = (stretched > otsu_threshold).astype(np.uint8) * 255

            if debug:
                debug_steps['06_otsu_threshold'] = otsu_binary

            # 直接在OTSU阈值结果上进行连通组件分析，不做严格筛选
            labeled, num_features = ndimage.label(otsu_binary > 127)

            # 只做最基本的筛选：长宽比和最小面积（非常宽松，保留所有可能的条带）
            min_aspect_ratio = 0.5  # 长宽比至少1.0（横向条带）
            max_aspect_ratio = 50.0  # 最大长宽比
            min_area = max(150, image_array.size // 20000)  # 最小面积（降低要求）

            # 直接提取所有连通组件作为条带（不做严格筛选）
            strips = []
            filtered_binary = np.zeros_like(otsu_binary)
            
            # 调试信息：统计连通组件
            if debug:
                print(f"  OTSU阈值: {otsu_threshold}, 检测到 {num_features} 个连通组件")
                print(f"  筛选条件: 最小面积={min_area}, 长宽比范围=[{min_aspect_ratio}, {max_aspect_ratio}]")

            filtered_count = 0
            for i in range(1, num_features + 1):
                mask = labeled == i
                coords = np.where(mask)
                if len(coords[0]) == 0:
                    continue

                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()
                width = x_max - x_min + 1
                height = y_max - y_min + 1
                area = mask.sum()
                aspect_ratio = width / height if height > 0 else 0

                # 只做最基本的筛选：长宽比和面积（非常宽松）
                if aspect_ratio >= min_aspect_ratio and aspect_ratio <= max_aspect_ratio and area >= min_area:
                    strips.append((x_min, y_min, width, height))
                    filtered_binary[mask] = 255
                    filtered_count += 1
                elif debug:
                    print(f"    组件 #{i} 被过滤: 面积={area}, 长宽比={aspect_ratio:.2f}, 尺寸={width}x{height}")

            # 如果没有满足条件的连通组件，至少保留OTSU阈值结果用于调试
            if filtered_count == 0 and debug:
                print(f"  警告: 没有连通组件满足筛选条件，保留OTSU阈值结果用于调试")
                filtered_binary = otsu_binary.copy()

            if debug:
                debug_steps['07_connected_components_filtered'] = filtered_binary
                print(f"  通过筛选的连通组件数量: {filtered_count}/{num_features}")

            # 保存调试图像
            if debug:
                self.save_debug_images(image_path, debug_steps, relative_path)

            # 按y坐标排序
            strips.sort(key=lambda s: s[1])
            print(f"  检测到 {len(strips)} 个黑色条带")

            if len(strips) > 0:
                for i, (x, y, w, h) in enumerate(strips):
                    print(f"    条带 #{i+1}: 位置({x}, {y}), 尺寸 {w}x{h}")

            # 标注图像
            annotated = self.annotate_image(pil_image, strips)

            # 确定输出路径（保持目录结构）
            if relative_path:
                # 保持相对目录结构
                output_file = self.output_dir / relative_path.parent / f"{image_path.stem}_annotated{image_path.suffix}"
            else:
                # 直接在输出目录
                output_file = self.output_dir / f"{image_path.stem}_annotated{image_path.suffix}"

            # 创建输出目录
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 保存结果（保持原文件格式）
            annotated.save(str(output_file))
            print(f"  结果保存到: {output_file}")

            return True, len(strips)

        except Exception as e:
            print(f"  错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, 0

    def process_all(self, recursive: bool = True, debug: bool = False):
        """
        处理所有图片文件

        参数:
            recursive: 是否递归查找子目录
        """
        if not self.input_dir.exists():
            print(f"错误: 输入目录不存在: {self.input_dir}")
            return

        # 查找PNG和TIF文件（支持大小写）
        if recursive:
            # 递归查找所有子目录
            image_files = (
                sorted(self.input_dir.rglob("*.png")) +
                sorted(self.input_dir.rglob("*.PNG")) +
                sorted(self.input_dir.rglob("*.tif")) +
                sorted(self.input_dir.rglob("*.TIF")) +
                sorted(self.input_dir.rglob("*.Tif"))
            )
        else:
            # 只在当前目录查找
            image_files = (
                sorted(self.input_dir.glob("*.png")) +
                sorted(self.input_dir.glob("*.PNG")) +
                sorted(self.input_dir.glob("*.tif")) +
                sorted(self.input_dir.glob("*.TIF")) +
                sorted(self.input_dir.glob("*.Tif"))
            )

        if len(image_files) == 0:
            print(f"在 {self.input_dir} 中未找到图片文件")
            print(f"提示: 请确认目录中有.png/.PNG或.tif/.TIF/.Tif格式的图片文件")
            return

        # 统计文件类型
        png_count = sum(1 for f in image_files if f.suffix.lower() == '.png')
        tif_count = sum(1 for f in image_files if f.suffix.lower() == '.tif')

        print("=" * 70)
        print("WB条带黑条识别")
        print("=" * 70)
        print(f"输入目录: {self.input_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"找到 {len(image_files)} 个图片文件 (PNG: {png_count}, TIF: {tif_count})")
        print("=" * 70)

        success_count = 0
        total_strips = 0

        for image_file in image_files:
            # 计算相对路径（用于保持输出目录结构）
            try:
                relative_path = image_file.relative_to(self.input_dir)
            except:
                relative_path = None

            success, strip_count = self.process_image(image_file, relative_path, debug=debug)
            if success:
                success_count += 1
                total_strips += strip_count

        print("\n" + "=" * 70)
        print(f"处理完成!")
        print(f"  成功处理: {success_count}/{len(image_files)} 张图片")
        print(f"  总共检测到: {total_strips} 个黑色条带")
        print(f"  结果保存在: {self.output_dir}")
        print("=" * 70)


    #-----------------------------------------------------------------
    #                          接入条带宝新增            
    #-----------------------------------------------------------------
    def detect_only(self, image_path: str, target_samples: int):
        
        try:
            

            # 图像加载
            pil_image = Image.open(str(image_path))
            image_array = np.array(pil_image)
            img_h, img_w = image_array.shape[:2]
            
            # 转灰度
            if len(image_array.shape) == 3:
                gray = np.dot(image_array[...,:3], [0.299, 0.587, 0.114]).astype(np.uint8)
            else:
                gray = image_array.copy()

        
            # 如果检测到深色背景（平均亮度 < 120），说明用户做了反转。
            # 先把它翻转回“浅色背景”，因为 blackhat_transform 函数是为此设计的。
            if np.mean(gray) < 120:
                gray = 255 - gray
            
            # 调用类内置的 Blackhat 函数
            # 使用 80 宽、20 高的参数，兼容厚条带
            feature_map = self.blackhat_transform(gray, kernel_width=80, kernel_height=20)

            # 信号增强：强制拉伸对比度，确保后续重心算法对弱条带也灵敏
            f_max = np.max(feature_map)
            if f_max > 0:
                feature_map = (feature_map.astype(np.float32) / f_max * 255).astype(np.uint8)
            
            # 纵向锁定高度
            row_sums = np.sum(feature_map, axis=1)
            y_peak = np.argmax(row_sums)
            row_thresh = np.max(row_sums) * 0.3
            y_indices = np.where(row_sums > row_thresh)[0]
            y_indices = y_indices[np.abs(y_indices - y_peak) < (img_h * 0.15)]
            
            if len(y_indices) > 0:
                lane_top, lane_bottom = y_indices[0], y_indices[-1]
            else:
                lane_top, lane_bottom = max(0, y_peak-15), min(img_h, y_peak+15)
            
            core_h = lane_bottom - lane_top
            final_h = int(core_h + 8)
            final_y = int(max(0, (lane_top + lane_bottom)/2 - final_h/2))

            # 横向重心定位
            lane_roi = feature_map[lane_top:lane_bottom, :]
            col_sums = np.sum(lane_roi, axis=0)
            col_sums_smooth = ndimage.gaussian_filter1d(col_sums, sigma=2.0)
            
            threshold = np.mean(col_sums_smooth) * 0.4
            labeled, num_islands = ndimage.label(col_sums_smooth > threshold)
            
            islands = []
            for i in range(1, num_islands + 1):
                idx = np.where(labeled == i)[0]
                if len(idx) < 5: continue
                weights = col_sums_smooth[idx]
                total_w = np.sum(weights)
                if total_w <= 0: continue
                
                mass_center = np.sum(idx * weights) / total_w
                islands.append({
                    "center": mass_center,
                    "energy": total_w,
                    "width": len(idx)
                })

            if not islands:
                print(json.dumps([]))
                return

            # 筛选与排序
            islands.sort(key=lambda x: x['energy'], reverse=True)
            selected = sorted(islands[:target_samples], key=lambda x: x['center'])

            # 计算全局等大宽度
            w_median = np.median([s['width'] for s in selected])
            if len(selected) > 1:
                avg_dist = np.mean(np.diff([s['center'] for s in selected]))
                # 1.6 倍扩张，0.92 间隙极限
                final_w = min(w_median * 1.6, avg_dist * 0.92)
            else:
                final_w = w_median * 1.6
            
            # 长方形保底比例
            final_w = int(max(final_h * 2.2, final_w))

            # 生成结果
            final_strips = []
            for s in selected:
                fx = int(s['center'] - final_w / 2)
                fx = max(0, min(fx, img_w - final_w))
                final_strips.append({"x": fx, "y": final_y, "w": final_w, "h": final_h})

            print(json.dumps(final_strips))
            
        except Exception as e:
            
            print(f"ALGORITHM ERROR: {str(e)}", file=sys.stderr)
            print(json.dumps([]))
#----------------------------------------------------------------------
#----------------------------------------------------------------------

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WB条带黑条识别脚本 - 识别PNG/TIF图片中的黑色条带")
    parser.add_argument("--input", "-i", type=str, default=r"D:\all\wb\test",
                       help="输入目录路径（包含PNG或TIF图片的目录）")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="输出目录路径（如果不指定，则自动在输入目录名后加_annotated）")
    parser.add_argument("--no-recursive", action="store_true",
                       help="不递归查找子目录（默认递归查找）")
    parser.add_argument("--debug", action="store_true",
                       help="保存每一步处理的中间结果图像到debug目录")

    # 解析命令行参数
    args = parser.parse_args()

    # 创建检测器
    detector = WBStripDetector(input_dir=args.input, output_dir=args.output)

    # 显示重要提示
    print("\n" + "=" * 60)
    print("WB图片条带检测与标注程序")
    print("=" * 60)
    print(f"输入目录: {detector.input_dir}")
    print(f"输出目录: {detector.output_dir}")
    print("\n重要提示：")
    print("  [OK] 所有输出文件名都添加了 '_annotated' 后缀")
    print("  [OK] 绝对不会覆盖原始图片文件")
    print("  [OK] 原始数据完全安全，不会被修改")
    print("  [OK] 支持PNG和TIF格式")
    print("  [OK] 自动保持子目录结构")
    print("=" * 60 + "\n")

    # 处理所有图片
    detector.process_all(recursive=not args.no_recursive, debug=args.debug)


if __name__ == "__main__":

    #print("DEBUG: Script started", file=sys.stderr)

    parser = argparse.ArgumentParser(description="WB条带识别")
    parser.add_argument("--input", "-i", type=str, help="输入目录或文件路径")
    parser.add_argument("--samples", type=int, default=6, help="需要识别的样本数量")
    
    # 新增参数供 Node.js 调用
    parser.add_argument("--json_mode", action="store_true", help="是否只输出JSON结果")
    parser.add_argument("--file", type=str, help="单个图片文件路径")

    args = parser.parse_args()
    detector = WBStripDetector()

    if args.json_mode and args.file:
        # 如果是 JSON 模式，只运行检测并退出
        detector.detect_only(args.file, args.samples) # 传入样本数
    else:
        # 否则运行你原来的批量处理逻辑
        detector.input_dir = Path(args.input) if args.input else detector.input_dir
        detector.process_all(debug=args.debug)
