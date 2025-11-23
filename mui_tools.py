# mcu_menu_designer_u8g2_final_complete.py
from PySide6.QtWidgets import (QApplication, QWidget, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFileDialog, QGroupBox, QComboBox, QCheckBox, QScrollArea, QTabWidget)
from PySide6.QtGui import (QTextOption, QPainter, QPixmap, QColor, QFont)
from PySide6.QtCore import Qt, QTime, QTimer

# ---------------- Menu 数据结构 ----------------
class MenuItem:
    _id_counter = 1
    def __init__(self, name="菜单项", is_exec=False, visible=True, parent=None):
        self.id = MenuItem._id_counter
        MenuItem._id_counter += 1
        self.name = name
        self.is_exec = is_exec
        self.visible = visible
        self.parent = parent
        self.children = []
        self.cursor_pos = 0
        self.callback_name = ""

    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        
        # 检查是否为最后一级菜单（叶子节点）
        self.check_and_set_leaf_nodes_exec()
    
    def check_and_set_leaf_nodes_exec(self):
        """自动检测并设置最后一级菜单为执行项"""
        def set_leaf_nodes_exec_recursive(node):
            if not node.children:  # 叶子节点
                node.is_exec = True
            else:
                node.is_exec = False  # 非叶子节点为子菜单
                for child in node.children:
                    set_leaf_nodes_exec_recursive(child)
        
        set_leaf_nodes_exec_recursive(self)

# ---------------- 菜单预览控件 ----------------
class MenuPreview(QWidget):
    def __init__(self, fb_w=128, fb_h=128, font_px=8):
        super().__init__()
        self.fb_w = fb_w
        self.fb_h = fb_h
        self.base_font_px = font_px
        self.screen_type = "OLED"  # 默认屏幕类型
        self.color_mode = "单色"   # 默认颜色模式
        
        # 设置默认颜色 - OLED模式使用蓝底黄色
        self.bg_color = QColor(0, 0, 128)  # 蓝色背景
        self.fg_color = QColor(255, 255, 0)  # 黄色字体
        self.selected_bg_color = QColor(255, 255, 0)  # 黄色选中背景
        self.selected_fg_color = QColor(0, 0, 128)  # 蓝色选中字体
        
        # 创建framebuffer，使用更高质量的图像格式
        self.framebuffer = QPixmap(self.fb_w, self.fb_h)
        self.framebuffer.fill(self.bg_color)
        
        # 设置framebuffer属性以提高文本渲染质量
        self.framebuffer.setDevicePixelRatio(1.0)
        
        self.update_preview_size()
        self.menu_root = None
        self.cursor_index = 0
        self.view_start = 0
        self.current_page = 0
        self.font_family = "Segoe UI"
        self.animating = False
        self.anim_progress = 0.0
        self.anim_prev_y = None
        self.anim_target_y = None
        self.anim_duration_ms = 140
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(15)
        self.anim_timer.timeout.connect(self._anim_tick)
        
        # 滚动指示器参数
        self.scroll_indicator_width = 10
        self.scroll_thumb_height = 20
        
        # 底部导航区域高度
        self.bottom_nav_height = font_px + 6

    def update_preview_size(self):
        """根据屏幕设置更新预览窗口大小"""
        # 获取预览大小设置
        preview_size_text = self.preview_size_combo.currentText() if hasattr(self, 'preview_size_combo') else "放大2倍"
        
        # 根据预览大小设置确定缩放比例
        if preview_size_text == "实际大小":
            scale_factor = 1
        elif preview_size_text == "放大1.5倍":
            scale_factor = 1.5
        elif preview_size_text == "放大2倍":
            scale_factor = 2
        elif preview_size_text == "放大3倍":
            scale_factor = 3
        else:
            scale_factor = 2  # 默认放大2倍
        
        # 计算预览窗口大小（包含边框和内边距）
        border_thickness = 4
        padding = 25
        
        frame_width = int(self.fb_w * scale_factor) + padding * 2
        frame_height = int(self.fb_h * scale_factor) + padding * 2
        
        # 设置预览窗口大小
        self.setFixedSize(frame_width, frame_height)

    def set_screen_type(self, screen_type, font_size="小(8px)", 
                        font_color="白色", bg_color="深蓝色", selected_bg="白色", selected_font="黑色", font_family=None):
        """设置屏幕类型和相关参数"""
        self.screen_type = screen_type
        if font_family:
            self.font_family = font_family
        
        # 根据屏幕类型调整参数 - 不再硬编码尺寸，使用当前设置
        if screen_type == "OLED":
            # OLED类型：使用当前framebuffer尺寸
            self.base_font_px = 8
            self.max_lines = 16
            
            # OLED模式：使用固定的蓝底黄色字体
            self.bg_color = QColor(0, 0, 128)  # 蓝色背景
            self.fg_color = QColor(255, 255, 0)  # 黄色字体
            self.selected_bg_color = QColor(255, 255, 0)  # 黄色选中背景
            self.selected_fg_color = QColor(0, 0, 128)  # 蓝色选中字体
        elif screen_type == "TFT":
            # TFT类型：使用当前framebuffer尺寸
            self.base_font_px = 12
            self.max_lines = 12
            
            # 设置背景颜色 - 支持HEX颜色
            if bg_color.startswith('#'):
                # HEX颜色输入
                color = QColor(bg_color)
                if color.isValid():
                    self.bg_color = color
                else:
                    self.bg_color = QColor(0, 64, 128)  # 默认深蓝色
            else:
                # 预设颜色名称
                if bg_color == "深蓝色":
                    self.bg_color = QColor(0, 64, 128)
                elif bg_color == "黑色":
                    self.bg_color = Qt.black
                elif bg_color == "深灰色":
                    self.bg_color = QColor(64, 64, 64)
                elif bg_color == "深绿色":
                    self.bg_color = QColor(0, 64, 32)
                elif bg_color == "深红色":
                    self.bg_color = QColor(64, 0, 32)
                elif bg_color == "深紫色":
                    self.bg_color = QColor(32, 0, 64)
                elif bg_color == "深青色":
                    self.bg_color = QColor(0, 64, 64)
                else:
                    self.bg_color = QColor(0, 64, 128)
            
            # 设置字体颜色 - 支持HEX颜色
            if font_color.startswith('#'):
                # HEX颜色输入
                color = QColor(font_color)
                if color.isValid():
                    self.fg_color = color
                else:
                    self.fg_color = Qt.white  # 默认白色
            else:
                # 预设颜色名称
                if font_color == "白色":
                    self.fg_color = Qt.white
                elif font_color == "黑色":
                    self.fg_color = Qt.black
                elif font_color == "红色":
                    self.fg_color = QColor(255, 0, 0)
                elif font_color == "绿色":
                    self.fg_color = QColor(0, 255, 0)
                elif font_color == "蓝色":
                    self.fg_color = QColor(0, 0, 255)
                elif font_color == "黄色":
                    self.fg_color = QColor(255, 255, 0)
                elif font_color == "青色":
                    self.fg_color = QColor(0, 255, 255)
                elif font_color == "品红色":
                    self.fg_color = QColor(255, 0, 255)
                elif font_color == "橙色":
                    self.fg_color = QColor(255, 165, 0)
                elif font_color == "紫色":
                    self.fg_color = QColor(128, 0, 128)
                else:
                    self.fg_color = Qt.white
            
            # 设置选中项背景颜色 - 支持HEX颜色
            if selected_bg.startswith('#'):
                # HEX颜色输入
                color = QColor(selected_bg)
                if color.isValid():
                    self.selected_bg_color = color
                else:
                    self.selected_bg_color = Qt.white  # 默认白色
            else:
                # 预设颜色名称
                if selected_bg == "白色":
                    self.selected_bg_color = Qt.white
                elif selected_bg == "浅灰色":
                    self.selected_bg_color = QColor(192, 192, 192)
                elif selected_bg == "浅蓝色":
                    self.selected_bg_color = QColor(173, 216, 230)
                elif selected_bg == "浅绿色":
                    self.selected_bg_color = QColor(144, 238, 144)
                elif selected_bg == "浅黄色":
                    self.selected_bg_color = QColor(255, 255, 224)
                elif selected_bg == "浅青色":
                    self.selected_bg_color = QColor(224, 255, 255)
                elif selected_bg == "浅红色":
                    self.selected_bg_color = QColor(255, 228, 225)
                else:
                    self.selected_bg_color = Qt.white
            
            # 设置选中项字体颜色 - 支持HEX颜色
            if selected_font.startswith('#'):
                # HEX颜色输入
                color = QColor(selected_font)
                if color.isValid():
                    self.selected_fg_color = color
                else:
                    self.selected_fg_color = Qt.black  # 默认黑色
            else:
                # 预设颜色名称
                if selected_font == "黑色":
                    self.selected_fg_color = Qt.black
                elif selected_font == "白色":
                    self.selected_fg_color = Qt.white
                elif selected_font == "红色":
                    self.selected_fg_color = QColor(255, 0, 0)
                elif selected_font == "绿色":
                    self.selected_fg_color = QColor(0, 255, 0)
                elif selected_font == "蓝色":
                    self.selected_fg_color = QColor(0, 0, 255)
                elif selected_font == "黄色":
                    self.selected_fg_color = QColor(255, 255, 0)
                elif selected_font == "青色":
                    self.selected_fg_color = QColor(0, 255, 255)
                elif selected_font == "品红色":
                    self.selected_fg_color = QColor(255, 0, 255)
                else:
                    self.selected_fg_color = Qt.black
        else:  # 默认使用OLED
            # 默认OLED类型：使用当前framebuffer尺寸
            self.base_font_px = 8
            self.max_lines = 16
            # 使用固定的蓝底黄色字体
            self.bg_color = QColor(0, 0, 128)  # 蓝色背景
            self.fg_color = QColor(255, 255, 0)  # 黄色字体
            self.selected_bg_color = QColor(255, 255, 0)  # 黄色选中背景
            self.selected_fg_color = QColor(0, 0, 128)  # 蓝色选中字体
        
        # 调整字体大小
        if "8px" in font_size:
            self.base_font_px = 8
        elif "12px" in font_size:
            self.base_font_px = 12
        elif "16px" in font_size:
            self.base_font_px = 16
        
        # 重新创建framebuffer，使用更好的图像格式
        self.framebuffer = QPixmap(self.fb_w, self.fb_h)
        self.framebuffer.setDevicePixelRatio(1.0)
        
        # 为OLED屏幕设置特定格式
        if "OLED" in self.screen_type:
            # 使用单色格式模拟OLED显示
            self.framebuffer.fill(self.bg_color)
        else:
            # 其他屏幕使用默认格式
            if hasattr(self, 'bg_color'):
                self.framebuffer.fill(self.bg_color)
            else:
                self.framebuffer.fill(Qt.black)
                
        self.update_preview_size()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制屏幕边框
        frame_rect = self.rect()
        inner_rect = frame_rect.adjusted(25, 25, -25, -25)
        
        # 计算实际缩放比例
        scale_factor = min(inner_rect.width() / self.fb_w, inner_rect.height() / self.fb_h)
        
        # 根据屏幕类型绘制边框
        if "OLED" in self.screen_type:
            painter.fillRect(frame_rect, QColor(40, 40, 40))
            painter.setPen(QColor(100, 100, 100))
            painter.drawRoundedRect(inner_rect.adjusted(-4, -4, 4, 4), 8, 8)
        elif "TFT" in self.screen_type:
            painter.fillRect(frame_rect, QColor(60, 60, 80))
            painter.setPen(QColor(100, 120, 140))
            painter.drawRoundedRect(inner_rect.adjusted(-4, -4, 4, 4), 12, 12)
        else:
            painter.fillRect(frame_rect, QColor(80, 80, 80))
            painter.setPen(QColor(120, 120, 120))
            painter.drawRoundedRect(inner_rect.adjusted(-4, -4, 4, 4), 8, 8)
        
        # 获取预览大小设置
        preview_size_text = self.preview_size_combo.currentText() if hasattr(self, 'preview_size_combo') else "放大2倍"
        
        # 根据预览大小设置确定缩放比例
        if preview_size_text == "实际大小":
            user_scale = 1
        elif preview_size_text == "放大1.5倍":
            user_scale = 1.5
        elif preview_size_text == "放大2倍":
            user_scale = 2
        elif preview_size_text == "放大3倍":
            user_scale = 3
        else:
            user_scale = 2  # 默认放大2倍
        
        # 使用用户设置的缩放比例
        int_scale = int(user_scale)
        if user_scale - int_scale > 0.7:
            int_scale += 1
        
        # 确保缩放后的尺寸是整数
        scaled_width = int(self.fb_w * int_scale)
        scaled_height = int(self.fb_h * int_scale)
        
        # 确保绘制位置是整数，避免亚像素模糊
        scaled_x = inner_rect.x() + (inner_rect.width() - scaled_width) // 2
        scaled_y = inner_rect.y() + (inner_rect.height() - scaled_height) // 2
        
        # 使用最适合的缩放方法
        if "OLED" in self.screen_type:
            # OLED屏幕使用最近邻插值保持像素清晰
            transformed = self.framebuffer.scaled(
                scaled_width, 
                scaled_height, 
                Qt.KeepAspectRatio, 
                Qt.FastTransformation
            )
        else:
            # 其他屏幕使用平滑变换
            transformed = self.framebuffer.scaled(
                scaled_width, 
                scaled_height, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
        
        painter.drawPixmap(scaled_x, scaled_y, transformed)
        
        # 移除滚动指示器显示
        # 滚动功能仍然可用，但不再显示视觉指示器

    def _draw_scrollbar(self, painter, inner_rect, scale_factor):
        """绘制滚动指示器"""
        # 计算滚动条位置和大小
        visible = [c for c in self.menu_root.children if c.visible]
        if len(visible) <= self.max_lines:
            return  # 不需要滚动条
            
        # 滚动条位置
        scrollbar_x = inner_rect.right() - 15 * scale_factor
        scrollbar_y = inner_rect.y()
        scrollbar_height = inner_rect.height()
        scrollbar_width = 10 * scale_factor
        
        # 绘制滚动条背景
        scrollbar_color = QColor(60, 60, 60) if "OLED" in self.screen_type else QColor(100, 100, 100)
        painter.fillRect(int(scrollbar_x), int(scrollbar_y), int(scrollbar_width), int(scrollbar_height), scrollbar_color)
        
        # 计算滑块大小和位置
        total_ratio = self.max_lines / len(visible)
        thumb_height = max(20 * scale_factor, int(scrollbar_height * total_ratio))
        
        # 当前位置比例
        current_pos_ratio = self.current_page / ((len(visible) - 1) // self.max_lines + 1) if len(visible) > self.max_lines else 0
        thumb_y = scrollbar_y + int((scrollbar_height - thumb_height) * current_pos_ratio)
        
        # 绘制滑块
        thumb_color = QColor(80, 255, 80) if "OLED" in self.screen_type else QColor(150, 150, 255)
        painter.fillRect(int(scrollbar_x), int(thumb_y), int(scrollbar_width), int(thumb_height), thumb_color)

    def render_menu(self):
        # 导入QFont类，确保在方法中可用
        from PySide6.QtGui import QFont
        
        if not self.menu_root:
            return
            
        visible = [c for c in self.menu_root.children if c.visible]
        self.framebuffer.fill(self.bg_color)
        
        line_h = self.base_font_px + 2
        max_lines = self.fb_h // line_h
        
        # 智能滚动逻辑：优化显示范围
        total = len(visible)
        if total == 0:
            painter = QPainter(self.framebuffer)
            painter.setPen(self.fg_color)
            painter.setFont(self._get_font())
            painter.drawText(5, line_h, "(空菜单)")
            painter.end()
            self.update()
            return
        
        # 绘制菜单项
        painter = QPainter(self.framebuffer)
        painter.setPen(self.fg_color)
        font = self._get_font()
        painter.setFont(font)
        
        # 设置渲染提示，提高文本清晰度
        # 对于像素级显示，禁用抗锯齿可能更清晰
        if "OLED" in self.screen_type:
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.TextAntialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)  # 禁用平滑变换
        else:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)  # 启用平滑变换
        
        # 计算显示起始位置（线性滚动）
        if max_lines >= total:
            start = 0
            self.view_start = 0
            self.show_scrollbar = False
        else:
            self.show_scrollbar = True
            if self.cursor_index < self.view_start:
                self.view_start = self.cursor_index
            elif self.cursor_index >= self.view_start + max_lines:
                self.view_start = self.cursor_index - max_lines + 1
            self.view_start = max(0, min(max(0, total - max_lines), self.view_start))
            start = self.view_start
        # 计算当前页码
        self.current_page = start // max_lines
        
 # 固定底部导航高度，始终显示底部导航组件
        bottom_nav_height = self.base_font_px + 6  # 底部导航区域高度
        
        # 调整最大行数以适应底部导航
        effective_height = self.fb_h - bottom_nav_height
        max_lines = effective_height // (self.base_font_px + 2)  # 重新计算最大行数
        max_lines = max(max_lines, 1)  # 确保至少显示一行
        
        # 重新计算显示起始位置（线性滚动）
        if max_lines >= total:
            start = 0
            self.view_start = 0
            self.show_scrollbar = False
        else:
            self.show_scrollbar = True
            if self.cursor_index < self.view_start:
                self.view_start = self.cursor_index
            elif self.cursor_index >= self.view_start + max_lines:
                self.view_start = self.cursor_index - max_lines + 1
            self.view_start = max(0, min(max(0, total - max_lines), self.view_start))
            start = self.view_start
        # 计算当前页码
        self.current_page = start // max_lines
        
        # 计算字符宽度和最大显示长度
        char_width = self.base_font_px * 0.6  # 估算字符宽度
        if "OLED" in self.screen_type:
            max_name_length = 12  # OLED屏幕显示较短
        elif "TFT" in self.screen_type:
            max_name_length = 14  # TFT屏幕显示适中
        else:
            max_name_length = 14  # 其他屏幕
            
        # 记录选中项目标位置用于动画
        calculated_selected_y = None
        offset = 0
        if getattr(self, 'content_animating', False):
            offset = int(self.content_from + (self.content_to - self.content_from) * max(0.0, min(1.0, self.content_progress)))
        for i in range(max_lines):
            idx = start + i
            if idx >= total:
                # 使用虚线填充空行
                if isinstance(self.fg_color, QColor):
                    painter.setPen(QColor(self.fg_color.red(), self.fg_color.green(), self.fg_color.blue(), 100))
                else:
                    # 处理GlobalColor类型
                    color = QColor(self.fg_color)
                    painter.setPen(QColor(color.red(), color.green(), color.blue(), 100))
                for x in range(0, self.fb_w, 8):
                    painter.drawPoint(x, i * line_h + line_h // 2 + offset)
                break
                
            item = visible[idx]
            y = i * line_h + line_h + offset
            
            # 计算缩进
            depth = 0
            p = item.parent
            while p and p != self.menu_root:
                depth += 1
                p = p.parent
            indent = "  " * depth
            
            # 处理过长的菜单名称
            display_name = item.name
            if len(display_name) > max_name_length:
                display_name = display_name[:max_name_length-2] + ".."
            
            # 绘制选中项
            if idx == self.cursor_index:
                calculated_selected_y = y
                # 动画时不立即填充背景，由动画条绘制；否则直接填充
                if not getattr(self, 'animating', False):
                    painter.fillRect(0, y - line_h, self.fb_w, line_h, self.selected_bg_color)
                painter.setPen(self.selected_fg_color)
                
                # 绘制选中项内容 - 简化符号，右侧不显示多余符号
                prefix = ">" if "OLED" in self.screen_type else ">"
                suffix = "" if not item.is_exec else ""  # 移除右侧多余符号
                text = f"{prefix} {indent}{display_name}{suffix}"
                # 使用更适合像素级显示的文本渲染方法
                if "OLED" in self.screen_type:
                    # OLED使用精确的像素位置，使用整数坐标避免亚像素模糊
                    text_x = 2
                    text_y = y - 1  # 微调垂直位置
                    painter.drawText(text_x, text_y, text)
                else:
                    # 其他屏幕使用居中对齐
                    rect = painter.boundingRect(2, y - line_h, self.fb_w - 4, line_h, Qt.AlignLeft | Qt.AlignVCenter, text)
                    painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)
            else:
                # 绘制普通项
                painter.setPen(self.fg_color)
                prefix = "  "
                suffix = ""  # 子菜单模式下右侧不显示额外符号
                text = f"{prefix} {indent}{display_name}{suffix}"
                # 使用更适合像素级显示的文本渲染方法
                if "OLED" in self.screen_type:
                    # OLED使用精确的像素位置，使用整数坐标避免亚像素模糊
                    text_x = 2
                    text_y = y - 1  # 微调垂直位置
                    painter.drawText(text_x, text_y, text)
                else:
                    # 其他屏幕使用居中对齐
                    rect = painter.boundingRect(2, y - line_h, self.fb_w - 4, line_h, Qt.AlignLeft | Qt.AlignVCenter, text)
                    painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        
        # 绘制选中条动画（轻量滑动）
        if getattr(self, 'animating', False) and self.anim_prev_y is not None and self.anim_target_y is not None:
            t = max(0.0, min(1.0, self.anim_progress))
            e = self._ease(t)
            anim_y = int(self.anim_prev_y + (self.anim_target_y - self.anim_prev_y) * e)
            col = QColor(self.selected_bg_color)
            col.setAlpha(int(180 + 75 * e))
            painter.fillRect(0, anim_y - line_h, self.fb_w, line_h, col)

        # 绘制底部固定导航组件，始终显示
        # 先导入QFont类，确保在整个方法中可用
        from PySide6.QtGui import QFont
        
        # 动态调整底部导航高度以适应内容
        if "OLED" in self.screen_type:
            # OLED底部导航：使用浅色背景区分区域
            bottom_bg_color = QColor(20, 20, 20)  # 比主背景稍亮的深灰色
            painter.fillRect(0, self.fb_h - bottom_nav_height, self.fb_w, bottom_nav_height, bottom_bg_color)
            
            # OLED分隔线：使用前景色绘制细线
            painter.setPen(self.fg_color)
            # 绘制像素级细线，使用点阵样式模拟OLED显示
            for x in range(0, self.fb_w, 2):
                painter.drawPoint(x, self.fb_h - bottom_nav_height)
            
            # OLED导航文本：使用前景色，像素级精确渲染
            painter.setPen(self.fg_color)
            # 使用与主菜单相同的字体，但不调整大小
            nav_font = self._get_font()
            # 保持原始字体大小，不调整底部字体
            nav_font.setStyleStrategy(QFont.NoAntialias)  # 禁用抗锯齿
            painter.setFont(nav_font)
        else:
            # TFT屏幕保持原有设置
            bottom_bg_color = QColor(50, 60, 80)
            painter.fillRect(0, self.fb_h - bottom_nav_height, self.fb_w, bottom_nav_height, bottom_bg_color)
            
            separator_color = QColor(120, 130, 150)
            painter.setPen(separator_color)
            painter.drawLine(0, self.fb_h - bottom_nav_height, self.fb_w, self.fb_h - bottom_nav_height)
            
            nav_text_color = QColor(240, 240, 250)
            painter.setPen(nav_text_color)
            nav_font = self._get_font()
            # 保持原始字体大小，不调整底部字体
            painter.setFont(nav_font)
        
        # 获取当前选中项的信息，整合到底部栏显示
        if self.cursor_index < len(visible):
            current_item = visible[self.cursor_index]
            if current_item.is_exec:
                # 执行项显示执行图标
                type_text = "● 执行"
            else:
                # 子菜单项显示子菜单图标
                type_text = "> 子菜单"
            
            # 添加位置信息到导航文本
            position_text = f"{self.cursor_index + 1}/{total}"
            nav_text = f"{position_text} {type_text}"
        else:
            nav_text = ""
        
        # 统一显示菜单指向信息，包含位置和类型
        if nav_text:
            # 设置底部导航专用字体，不受主字体设置影响
            from PySide6.QtGui import QFont
            if "OLED" in self.screen_type:
                # OLED使用更大的字体设置
                nav_font = QFont("Consolas", 11)  # 使用Consolas字体，更清晰的等宽字体
                nav_font.setPixelSize(11)  # 使用像素大小而不是点大小，更精确
                nav_font.setStyleStrategy(QFont.NoAntialias)  # 禁用抗锯齿
                nav_font.setHintingPreference(QFont.PreferNoHinting)  # 禁用字体提示，避免模糊
                nav_font.setBold(False)  # 取消粗体，提高清晰度
                nav_font.setKerning(False)  # 禁用字距调整
                painter.setFont(nav_font)
                
                # 设置渲染提示，确保像素级清晰
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.setRenderHint(QPainter.TextAntialiasing, False)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
                
                # OLED使用精确的像素位置
                text_width = len(nav_text) * 6  # 11px字体的字符宽度约6px
                text_x = max(2, (self.fb_w - text_width) // 2)
                # 使用整数坐标，避免亚像素模糊
                painter.drawText(int(text_x), self.fb_h - 2, nav_text)
            else:
                # TFT使用更大的字体设置
                nav_font = QFont("Segoe UI", 13)  # 使用Segoe UI字体，更清晰
                nav_font.setPixelSize(13)  # 使用像素大小
                nav_font.setStyleStrategy(QFont.PreferAntialias)
                nav_font.setHintingPreference(QFont.PreferFullHinting)
                nav_font.setBold(False)
                painter.setFont(nav_font)
                
                # 设置渲染提示
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.TextAntialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                
                # 使用精确的文本渲染
                rect = painter.boundingRect(0, self.fb_h - bottom_nav_height, self.fb_w, bottom_nav_height, Qt.AlignCenter, nav_text)
                painter.drawText(rect, Qt.AlignCenter, nav_text)
            
            # 移除分页导航指示器中的三角形箭头
            # 保留分页功能但不显示箭头图标
        
        painter.end()

        # 更新动画状态：检测选中项位置变更，启动动画
        if calculated_selected_y is not None:
            if self.anim_target_y is None:
                self.anim_target_y = calculated_selected_y
                self.anim_prev_y = calculated_selected_y
            elif calculated_selected_y != self.anim_target_y:
                # 根据移动行数自适应动画时长
                moved_lines = max(1, int(abs(calculated_selected_y - self.anim_target_y) / max(1, line_h)))
                self.anim_duration_ms = min(240, 120 + 40 * (moved_lines - 1))
                self.anim_prev_y = self.anim_target_y
                self.anim_target_y = calculated_selected_y
                self.anim_progress = 0.0
                self.animating = True
                if hasattr(self, 'anim_timer') and not self.anim_timer.isActive():
                    self.anim_timer.start()

        if start != getattr(self, 'last_start', 0):
            delta = start - getattr(self, 'last_start', 0)
            step = (self.base_font_px + 2) * (1 if delta > 0 else -1) * min(3, abs(delta))
            self.content_from = step
            self.content_to = 0.0
            self.content_progress = 0.0
            self.content_animating = True
            self.last_start = start
            if hasattr(self, 'anim_timer') and not self.anim_timer.isActive():
                self.anim_timer.start()

        self.update()
    
    def mousePressEvent(self, event):
        """处理鼠标点击事件，实现底部导航功能"""
        if event.button() == Qt.LeftButton:
            # 获取点击位置
            click_x = event.position().x()
            click_y = event.position().y()
            
            # 计算内部区域位置（排除边框）
            frame_rect = self.rect()
            inner_rect = frame_rect.adjusted(25, 25, -25, -25)
            
            # 获取预览大小设置
            preview_size_text = self.preview_size_combo.currentText() if hasattr(self, 'preview_size_combo') else "放大2倍"
            
            # 根据预览大小设置确定缩放比例
            if preview_size_text == "实际大小":
                user_scale = 1
            elif preview_size_text == "放大1.5倍":
                user_scale = 1.5
            elif preview_size_text == "放大2倍":
                user_scale = 2
            elif preview_size_text == "放大3倍":
                user_scale = 3
            else:
                user_scale = 2  # 默认放大2倍
            
            # 计算缩放后的屏幕区域
            int_scale = int(user_scale)
            if user_scale - int_scale > 0.7:
                int_scale += 1
            
            scaled_width = int(self.fb_w * int_scale)
            scaled_height = int(self.fb_h * int_scale)
            scaled_x = inner_rect.x() + (inner_rect.width() - scaled_width) // 2
            scaled_y = inner_rect.y() + (inner_rect.height() - scaled_height) // 2
            
            # 底部导航区域高度（缩放后）
            scaled_bottom_nav_height = self.bottom_nav_height * int_scale
            scaled_bottom_nav_y = scaled_y + scaled_height - scaled_bottom_nav_height
            
            # 检查点击是否在底部导航区域内
            if (scaled_x <= click_x <= scaled_x + scaled_width and 
                scaled_bottom_nav_y <= click_y <= scaled_y + scaled_height):
                
                # 计算点击位置在底部导航区域的相对位置
                relative_x = click_x - scaled_x
                relative_y = click_y - scaled_bottom_nav_y
                
                # 获取可见菜单项
                if self.menu_root:
                    visible = [c for c in self.menu_root.children if c.visible]
                    total = len(visible)
                    if total > 0:
                        # 计算最大行数
                        effective_height = self.fb_h - self.bottom_nav_height
                        max_lines = effective_height // (self.base_font_px + 2)
                        max_lines = max(max_lines, 1)
                        
                        # 检查是否点击了左箭头导航
                        if relative_x < 30 and self.current_page > 0:
                            # 上一页
                            self.cursor_index = max(0, self.cursor_index - max_lines)
                            self.render_menu()
                        
                        # 检查是否点击了右箭头导航
                        elif relative_x > scaled_width - 30 and self.current_page < (total - 1) // max_lines:
                            # 下一页
                            self.cursor_index = min(total - 1, self.cursor_index + max_lines)
                            self.render_menu()
        
        # 调用父类的鼠标事件处理
        super().mousePressEvent(event)

    def _anim_tick(self):
        any_anim = False
        if getattr(self, 'animating', False):
            step = 15.0 / float(getattr(self, 'anim_duration_ms', 140))
            self.anim_progress += step
            if self.anim_progress >= 1.0:
                self.anim_progress = 1.0
                self.animating = False
            else:
                any_anim = True
        if getattr(self, 'content_animating', False):
            step_c = 15.0 / float(getattr(self, 'anim_duration_ms', 140))
            self.content_progress += step_c
            if self.content_progress >= 1.0:
                self.content_progress = 1.0
                self.content_animating = False
                self.content_from = 0.0
                self.content_to = 0.0
                self.content_progress = 0.0
            else:
                any_anim = True
        if not any_anim:
            if hasattr(self, 'anim_timer'):
                self.anim_timer.stop()
        self.render_menu()

    def _ease(self, t):
        return t * t * (3.0 - 2.0 * t)

    def _get_font(self):
        """获取合适的字体"""
        from PySide6.QtGui import QFont
        fam = getattr(self, 'font_family', None) or "Segoe UI"
        font = QFont(fam, max(self.base_font_px, 10))
        if "OLED" in self.screen_type:
            font.setStyleStrategy(QFont.NoAntialias)
            font.setHintingPreference(QFont.PreferFullHinting)
        else:
            font.setStyleStrategy(QFont.PreferAntialias)
            
        font.setBold(False)  # 禁用粗体，减少像素化
        font.setStyleHint(QFont.Monospace)  # 使用等宽字体
        font.setKerning(False)  # 禁用字距调整，提高清晰度
        font.setFixedPitch(True)  # 使用固定间距
        # 确保字体大小不会太小
        if self.screen_type == "128x64 OLED" and font.pointSize() < 8:
            font.setPointSize(8)
        return font

# ---------------- 主设计器 ----------------
class MenuDesigner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCU 菜单设计器 - U8G2 完整版")
        self.resize(1270,700)
        
        # 添加按键防抖机制
        from PySide6.QtCore import QTimer
        self.key_debounce_timer = None
        self.key_processing = False
        
        # 应用现代化样式表
        self.apply_modern_style()
        
        # 保存当前设置状态，避免切换时丢失
        self.current_settings = {
            'font_size': '中(12px)',
            'color_mode': '单色',
            'preview_size': '实际大小',
            'bg_color': '#004080',
            'font_color': '#FFFFFF',
            'selected_bg': '#FFFFFF',
            'selected_font': '#000000',
            'font_family': 'Segoe UI',
            'emit_font_array': True,
            'emit_draw_skeleton': True,
            'emit_cjk_subset': True,
            'export_no_u8g2': False
        }
        
        # 加载保存的设置
        self.load_settings()
        
        # 应用加载的设置到界面
        self.apply_loaded_settings()

        # 根菜单
        self.menu_root = MenuItem("根菜单", is_exec=False)
        self.menu_root.add_child(MenuItem("系统设置", is_exec=False))
        self.menu_root.add_child(MenuItem("数据显示", is_exec=False))
        self.menu_root.add_child(MenuItem("设备控制", is_exec=False))
        self.menu_root.add_child(MenuItem("通信设置", is_exec=False))
        self.menu_root.add_child(MenuItem("时间日期", is_exec=False))
        self.menu_root.add_child(MenuItem("网络配置", is_exec=False))
        self.menu_root.add_child(MenuItem("安全设置", is_exec=False))
        self.menu_root.add_child(MenuItem("用户管理", is_exec=False))
        self.menu_root.add_child(MenuItem("日志记录", is_exec=False))
        self.menu_root.add_child(MenuItem("系统信息", is_exec=False))
        self.menu_root.add_child(MenuItem("诊断工具", is_exec=False))
        self.menu_root.add_child(MenuItem("固件更新", is_exec=False))
        self.menu_root.add_child(MenuItem("备份恢复", is_exec=False))
        self.menu_root.add_child(MenuItem("工厂重置", is_exec=False))
        self.current_node = self.menu_root

        # 主布局 - 三列布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)  # 增加控件间距
        main_layout.setContentsMargins(15, 15, 15, 15)  # 增加边距

        # === 左侧：菜单树 ===
        left_widget = QWidget()
        left_widget.setMinimumWidth(360)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)  # 增加内部间距
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 面包屑与搜索行
        self.menu_breadcrumb = QLabel("根菜单")
        self.menu_breadcrumb.setStyleSheet("background:#1f1f1f; color:#a8e1ff; border:1px solid #303030; border-radius:6px; padding:6px 10px; font-weight:600;")
        left_layout.addWidget(self.menu_breadcrumb)

        search_row = QHBoxLayout()
        self.menu_search_edit = QLineEdit()
        self.menu_search_edit.setPlaceholderText("搜索菜单项")
        search_row.addWidget(self.menu_search_edit)
        self.menu_expand_btn = QPushButton("展开")
        self.menu_collapse_btn = QPushButton("折叠")
        self.menu_expand_btn.setFixedWidth(56)
        self.menu_collapse_btn.setFixedWidth(56)
        search_row.addWidget(self.menu_expand_btn)
        search_row.addWidget(self.menu_collapse_btn)
        left_layout.addLayout(search_row)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["名称", "信息"])
        self.tree.itemClicked.connect(self.on_tree_select)
        self.tree.setMinimumHeight(400)  # 设置最小高度
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(14)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setStyleSheet("QTreeWidget { background:#1f1f1f; color:#e6e6e6; border:1px solid #303030; outline:none; }\n"
                               "QTreeWidget::item { padding:6px 10px; height:26px; border-bottom:1px solid #2a2a2a; }\n"
                               "QTreeWidget::item:hover { background:#2a2a2a; }\n"
                               "QTreeWidget::item:selected { background:#2b2f3a; color:#ffffff; border-left:3px solid #3DA9FC; font-weight:600; }\n"
                               "QTreeWidget::header { background:#1e1e1e; color:#a0a0a0; border:none; padding:6px 10px; }")
        from PySide6.QtWidgets import QHeaderView
        hdr = self.tree.header()
        hdr.setStretchLastSection(True)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.refresh_tree()
        left_layout.addWidget(self.tree)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        left_layout.addStretch()

        # 连接搜索与展开折叠
        self.menu_search_edit.textChanged.connect(self.filter_menu_tree)
        self.menu_expand_btn.clicked.connect(lambda: self.tree.expandAll())
        self.menu_collapse_btn.clicked.connect(lambda: self.tree.collapseAll())
        
        main_layout.addWidget(left_widget, 0)  # 左侧固定宽度

        # === 中间：菜单预览 ===
        middle_widget = QWidget()
        middle_widget.setMinimumWidth(400)  # 设置最小宽度
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setSpacing(10)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        # 菜单预览组
        preview_group = QGroupBox("菜单预览")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setSpacing(8)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        
        # 创建预览控件 - 调整高度以容纳调试信息框
        self.preview = MenuPreview()
        self.preview.setMinimumHeight(360)  # 进一步减小预览高度，为调试框留出更多空间
        preview_layout.addWidget(self.preview, 1)  # 使用拉伸因子1，让预览控件占用剩余空间
        # 调试信息框 - 增大尺寸优化
        debug_group = QGroupBox("调试信息")
        debug_group.setFixedHeight(300)  # 增大高度到300px
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setSpacing(0)  # 完全无间距
        debug_layout.setContentsMargins(1, 1, 1, 1)  # 最小边距
        debug_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # 创建调试信息显示文本框 - 增大尺寸设计
        import sys
        from io import StringIO

        class DebugStreamRedirector(StringIO):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr

            def write(self, message):
                # 保留原始输出
                self.original_stdout.write(message)
                self.original_stderr.write(message)

                # 更新调试窗口
                current_text = self.text_widget.toPlainText()
                if current_text == "等待按键操作...":
                    new_text = message.strip()
                else:
                    lines = current_text.split('\n')
                    lines.insert(0, message.strip())
                    if len(lines) > 20:
                        lines = lines[:20]
                    new_text = '\n'.join(lines)
                
                try:
                    lines = new_text.split('\n') if new_text else []
                    html_lines = []
                    if lines:
                        latest = lines[0]
                        lt = latest.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                        if '按键:' in latest:
                            html_lines.append(f"<span style=\"display:block;background:#FFF59D;color:#000000;font-weight:700;padding:2px 4px;\">{lt}</span>")
                        else:
                            html_lines.append(f"<span style=\"color:#e0e0e0;\">{lt}</span>")
                        for l in lines[1:]:
                            t = l.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                            if '按键:' in l:
                                html_lines.append(f"<span style=\"color:#FFD54F;font-weight:700;\">{t}</span>")
                            else:
                                html_lines.append(f"<span style=\"color:#e0e0e0;\">{t}</span>")
                        self.text_widget.setHtml("<br/>".join(html_lines))
                    else:
                        self.text_widget.setHtml("<span style=\"color:#808080\">等待按键操作...</span>")
                except:
                    # 兜底：纯文本
                    self.text_widget.setPlainText(new_text)

            def flush(self):
                self.original_stdout.flush()
                self.original_stderr.flush()

        self.debug_text = QTextEdit("等待按键操作...")
        self.debug_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 2px solid #555555;
                border-radius: 0px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
        """)
        self.debug_text.setReadOnly(True)
        self.debug_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.debug_text.setFixedHeight(285)
        self.debug_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        debug_layout.addWidget(self.debug_text)

        # 设置标准输出重定向
        self.stdout_redirector = DebugStreamRedirector(self.debug_text)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stdout_redirector
        # 确保完全闭合，无弹性空间
        
        preview_layout.addWidget(debug_group)
        
        middle_layout.addWidget(preview_group)
        # 移除弹性空间，让调试信息框自然位于底部
        # middle_layout.addStretch()  # 注释掉弹性空间，确保底部对齐
        
        main_layout.addWidget(middle_widget, 1)  # 中间自适应宽度

        # === 右侧：配置与操作 ===
        right_widget = QWidget()
        right_widget.setMinimumWidth(400)
        right_widget.setMaximumWidth(600)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 首先添加按键模拟组到右下角
        keys_group = QGroupBox("按键模拟")
        keys_layout = QVBoxLayout(keys_group)
        keys_layout.setSpacing(8)
        keys_layout.setContentsMargins(12, 12, 12, 12)
        
        # Core key button layouts
        keys_grid_layout = QVBoxLayout()
        keys_grid_layout.setSpacing(10)
        
        # Top row - centered up button
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.key_up_btn = QPushButton("↑")
        self.key_up_btn.setProperty("class", "key-btn")
        self.key_up_btn.setFixedSize(50, 40)  # Main action button
        self.key_up_btn.setStyleSheet("""
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4a4a4a, stop:1 #3a3a3a);
    border: 2px solid #555555;
    border-radius: 6px;
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
    padding: 5px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5a5a5a, stop:1 #4a4a4a);
    border-color: #0078d4;
}
QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border-color: #005a9e;
            }
        """)
        top_row.addWidget(self.key_up_btn)
        top_row.addStretch()
        
        # 下方三个按键（水平排列）
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)  # 减小按键间距
        bottom_row.addStretch()
        
        # 左键
        self.key_left_btn = QPushButton("←")
        self.key_left_btn.setProperty("class", "key-btn")
        self.key_left_btn.setFixedSize(50, 40)  # 统一大小
        self.key_left_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                border: 2px solid #555555;
                border-radius: 6px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_left_btn)
        
        # 下键
        self.key_down_btn = QPushButton("↓")
        self.key_down_btn.setProperty("class", "key-btn")
        self.key_down_btn.setFixedSize(50, 40)  # 统一大小
        self.key_down_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                border: 2px solid #555555;
                border-radius: 6px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_down_btn)
        bottom_row.addStretch()  # 添加右侧弹性空间
        
        # 右键
        self.key_right_btn = QPushButton("→")
        self.key_right_btn.setProperty("class", "key-btn")
        self.key_right_btn.setFixedSize(50, 40)  # 统一大小
        self.key_right_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                border: 2px solid #555555;
                border-radius: 6px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_right_btn)
        bottom_row.addStretch()  # 保持布局平衡
        
        # 将行添加到按键布局
        keys_grid_layout.addLayout(top_row)
        keys_grid_layout.addLayout(bottom_row)
        
        # 创建嵌入式风格的按键容器
        keys_container = QWidget()
        keys_container.setLayout(keys_grid_layout)
        keys_container.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border: 2px solid #1a1a1a;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        keys_container_layout = QHBoxLayout()
        keys_container_layout.addStretch()
        keys_container_layout.addWidget(keys_container)
        keys_container_layout.addStretch()
        
        keys_layout.addLayout(keys_container_layout)
        
        # 连接按键事件
        self.key_up_btn.clicked.connect(lambda: self.on_key("Up"))
        self.key_down_btn.clicked.connect(lambda: self.on_key("Down"))
        self.key_left_btn.clicked.connect(lambda: self.on_key("Left"))
        self.key_right_btn.clicked.connect(lambda: self.on_key("Right"))
        # 导入选项卡控件
        from PySide6.QtWidgets import QTabWidget
        
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)  # 选项卡在上方
        
        # === 选项卡1: 菜单操作 ===
        menu_tab = QWidget()
        menu_tab_layout = QVBoxLayout(menu_tab)
        menu_tab_layout.setSpacing(10)
        menu_tab_layout.setContentsMargins(12, 12, 12, 12)
        
        # 菜单选择提示
        self.selection_label = QLabel("请选择一个菜单项进行编辑")
        self.selection_label.setWordWrap(True)
        self.selection_label.setStyleSheet("color: #a0a0a0; font-style: italic; padding: 10px;")
        self.selection_label.setAlignment(Qt.AlignCenter)
        menu_tab_layout.addWidget(self.selection_label)

        # 属性编辑区域（初始隐藏）
        self.properties_widget = QWidget()
        self.properties_widget.setVisible(False)
        properties_layout = QVBoxLayout(self.properties_widget)
        properties_layout.setSpacing(8)
        properties_layout.setContentsMargins(0, 0, 0, 0)

        # 当前选中项信息
        self.current_item_label = QLabel()
        self.current_item_label.setStyleSheet("font-weight: 600; color: #0078d4; padding: 5px; background-color: #f0f8ff; border-radius: 4px; margin-bottom: 10px;")
        properties_layout.addWidget(self.current_item_label)

        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self.update_name)
        self.name_edit.setMinimumHeight(30)  # 增加输入框高度
        properties_layout.addWidget(QLabel("菜单名称:"))
        properties_layout.addWidget(self.name_edit)

        self.callback_edit = QLineEdit()
        self.callback_edit.setMinimumHeight(30)  # 增加输入框高度
        properties_layout.addWidget(QLabel("回调函数名:"))
        properties_layout.addWidget(self.callback_edit)
        self.callback_edit.editingFinished.connect(self.update_callback)

        menu_tab_layout.addWidget(self.properties_widget)

        # 分隔线
        line = QLabel()
        line.setStyleSheet("border: none; border-top: 1px solid #e1e8ed; margin: 10px 0;")
        menu_tab_layout.addWidget(line)

        # 按钮布局 - 使用水平布局使按钮更紧凑
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.add_btn = QPushButton("添加子菜单")
        self.add_btn.clicked.connect(self.add_menu)
        self.add_btn.setMinimumHeight(35)  # 增加按钮高度
        button_layout.addWidget(self.add_btn)

        self.del_btn = QPushButton("删除菜单")
        self.del_btn.clicked.connect(self.del_menu)
        self.del_btn.setMinimumHeight(35)  # 增加按钮高度
        button_layout.addWidget(self.del_btn)
        
        menu_tab_layout.addLayout(button_layout)

        menu_tab_layout.addWidget(QLabel(" "))
        self.export_btn = QPushButton("导出MUI C代码")
        self.export_btn.setProperty("class", "primary")  # 设置为主要按钮样式
        self.export_btn.clicked.connect(self.export_code)
        self.export_btn.setMinimumHeight(40)  # 增加导出按钮高度
        menu_tab_layout.addWidget(self.export_btn)
        menu_tab_layout.addStretch()
        
        # 添加菜单操作选项卡
        self.tab_widget.addTab(menu_tab, "📝 菜单")
        
        # === 选项卡2: 屏幕配置 ===
        config_tab = QWidget()
        config_tab_layout = QVBoxLayout(config_tab)
        config_tab_layout.setSpacing(10)
        config_tab_layout.setContentsMargins(15, 15, 15, 15)
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        config_inner = QWidget()
        config_inner_layout = QVBoxLayout(config_inner)
        config_inner_layout.setSpacing(10)
        config_inner_layout.setContentsMargins(0, 0, 0, 0)
        
        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        
        # 屏幕类型选择
        screen_type_layout = QHBoxLayout()
        screen_type_layout.addWidget(QLabel("屏幕类型:"))
        self.screen_type_combo = QComboBox()
        self.screen_type_combo.addItems(["OLED", "TFT"])
        self.screen_type_combo.currentTextChanged.connect(self.on_screen_type_changed)
        screen_type_layout.addWidget(self.screen_type_combo)
        screen_type_layout.addStretch()
        
        # 屏幕尺寸设置
        screen_size_layout = QHBoxLayout()
        screen_size_layout.addWidget(QLabel("屏幕尺寸:"))
        self.screen_width_edit = QLineEdit("128")
        self.screen_width_edit.setMaximumWidth(50)
        screen_size_layout.addWidget(self.screen_width_edit)
        screen_size_layout.addWidget(QLabel("×"))
        self.screen_height_edit = QLineEdit("128")
        self.screen_height_edit.setMaximumWidth(50)
        screen_size_layout.addWidget(self.screen_height_edit)
        self.apply_size_btn = QPushButton("应用")
        self.apply_size_btn.clicked.connect(self.on_apply_screen_size)
        self.apply_size_btn.setMaximumWidth(50)
        screen_size_layout.addWidget(self.apply_size_btn)
        screen_size_layout.addStretch()
        
        basic_layout.addLayout(screen_type_layout)
        basic_layout.addLayout(screen_size_layout)
        
        # 显示设置组
        display_group = QGroupBox("显示设置")
        display_layout = QVBoxLayout(display_group)
        display_layout.setSpacing(8)
        display_layout.setContentsMargins(10, 10, 10, 10)
        
        # 颜色模式选项已移除
        
        # 字体大小选择
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["小(8px)", "中(12px)", "大(16px)"])
        self.font_size_combo.setCurrentText("中(12px)")
        self.font_size_combo.currentTextChanged.connect(self.on_screen_config_changed)
        font_size_layout.addWidget(self.font_size_combo)
        font_size_layout.addStretch()
        font_family_layout = QHBoxLayout()
        font_family_layout.addWidget(QLabel("默认字体:"))
        self.default_font_combo = QComboBox()
        self.default_font_combo.addItems(["Segoe UI","Arial","Times New Roman","Courier New","Microsoft YaHei","SimSun","SimHei","KaiTi"]) 
        self.default_font_combo.setCurrentText("Segoe UI")
        font_family_layout.addWidget(self.default_font_combo)
        self.default_font_combo.currentTextChanged.connect(self.on_screen_config_changed)
        font_family_layout.addStretch()
        
        # 预览窗口大小设置
        preview_size_layout = QHBoxLayout()
        preview_size_layout.addWidget(QLabel("预览缩放:"))
        self.preview_size_combo = QComboBox()
        self.preview_size_combo.addItems(["实际大小", "放大1.5倍", "放大2倍", "放大3倍"])
        self.preview_size_combo.setCurrentText("实际大小")
        self.preview_size_combo.currentTextChanged.connect(self.on_preview_size_changed)
        preview_size_layout.addWidget(self.preview_size_combo)
        preview_size_layout.addStretch()
        
        # 移除颜色模式布局
        display_layout.addLayout(font_size_layout)
        display_layout.addLayout(font_family_layout)
        display_layout.addLayout(preview_size_layout)
        
        # 颜色配置组（仅TFT模式）
        self.color_group = QGroupBox("颜色配置 (TFT模式)")
        color_layout = QVBoxLayout(self.color_group)
        color_layout.setSpacing(8)
        color_layout.setContentsMargins(10, 10, 10, 10)
        
        # 背景颜色选择（移除 HEX 输入）
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("背景颜色:"))
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setText("选择颜色")
        self.bg_color_btn.setStyleSheet("background-color: rgb(0, 64, 128); color: white;")
        self.bg_color_btn.setProperty("class", "color-btn")
        self.bg_color_btn.clicked.connect(lambda: self.choose_color('bg'))
        self.bg_color_btn.setMaximumWidth(80)
        bg_color_layout.addWidget(self.bg_color_btn)
        bg_color_layout.addStretch()
        
        # 字体颜色选择（移除 HEX 输入）
        font_color_layout = QHBoxLayout()
        font_color_layout.addWidget(QLabel("字体颜色:"))
        self.font_color_btn = QPushButton()
        self.font_color_btn.setText("选择颜色")
        self.font_color_btn.setStyleSheet("background-color: rgb(255, 255, 255); color: black;")
        self.font_color_btn.setProperty("class", "color-btn")
        self.font_color_btn.clicked.connect(lambda: self.choose_color('font'))
        self.font_color_btn.setMaximumWidth(80)
        font_color_layout.addWidget(self.font_color_btn)
        font_color_layout.addStretch()
        
        # 选中项背景颜色（移除 HEX 输入）
        selected_bg_layout = QHBoxLayout()
        selected_bg_layout.addWidget(QLabel("选中背景:"))
        self.selected_bg_btn = QPushButton()
        self.selected_bg_btn.setText("选择颜色")
        self.selected_bg_btn.setStyleSheet("background-color: rgb(255, 255, 255); color: black;")
        self.selected_bg_btn.setProperty("class", "color-btn")
        self.selected_bg_btn.clicked.connect(lambda: self.choose_color('selected_bg'))
        self.selected_bg_btn.setMaximumWidth(80)
        selected_bg_layout.addWidget(self.selected_bg_btn)
        selected_bg_layout.addStretch()
        
        # 选中项字体颜色（移除 HEX 输入）
        selected_font_layout = QHBoxLayout()
        selected_font_layout.addWidget(QLabel("选中字体:"))
        self.selected_font_btn = QPushButton()
        self.selected_font_btn.setText("选择颜色")
        self.selected_font_btn.setStyleSheet("background-color: rgb(0, 0, 0); color: white;")
        self.selected_font_btn.setProperty("class", "color-btn")
        self.selected_font_btn.clicked.connect(lambda: self.choose_color('selected_font'))
        self.selected_font_btn.setMaximumWidth(80)
        selected_font_layout.addWidget(self.selected_font_btn)
        selected_font_layout.addStretch()
        
        color_layout.addLayout(bg_color_layout)
        color_layout.addLayout(font_color_layout)
        color_layout.addLayout(selected_bg_layout)
        color_layout.addLayout(selected_font_layout)
        
        # 代码生成设置组
        codegen_group = QGroupBox("代码生成")
        codegen_layout = QVBoxLayout(codegen_group)
        codegen_layout.setSpacing(8)
        codegen_layout.setContentsMargins(10, 10, 10, 10)
        self.cb_emit_font = QCheckBox("包含 ASCII 字体数组")
        self.cb_emit_font.setChecked(True)
        self.cb_emit_draw = QCheckBox("包含绘制函数骨架")
        self.cb_emit_draw.setChecked(True)
        self.cb_emit_cjk = QCheckBox("包含中文子集字库（来自菜单使用的汉字）")
        self.cb_emit_cjk.setChecked(True)
        self.cb_no_u8g2 = QCheckBox("导出不依赖U8G2的代码（含移植接口与示例）")
        self.cb_no_u8g2.setChecked(False)
        self.cb_emit_font.stateChanged.connect(lambda _: self.save_settings())
        self.cb_emit_draw.stateChanged.connect(lambda _: self.save_settings())
        self.cb_emit_cjk.stateChanged.connect(lambda _: self.save_settings())
        self.cb_no_u8g2.stateChanged.connect(lambda _: self.save_settings())
        codegen_layout.addWidget(self.cb_emit_font)
        codegen_layout.addWidget(self.cb_emit_draw)
        codegen_layout.addWidget(self.cb_emit_cjk)
        codegen_layout.addWidget(self.cb_no_u8g2)

        # 添加到配置选项卡（滚动容器）
        config_inner_layout.addWidget(basic_group)
        config_inner_layout.addWidget(display_group)
        config_inner_layout.addWidget(self.color_group)
        config_inner_layout.addWidget(codegen_group)
        config_inner_layout.addStretch()
        config_scroll.setWidget(config_inner)
        config_tab_layout.addWidget(config_scroll)
        
        # 添加配置选项卡
        self.tab_widget.addTab(config_tab, "⚙️ 配置")
        
        # 添加选项卡控件到右侧布局
        right_layout.addWidget(self.tab_widget)
        
        # 将按键组添加到右侧布局的底部（右下角位置）
        right_layout.addWidget(keys_group)
        
        main_layout.addWidget(right_widget, 0)  # 右侧固定宽度
        
        # 现在设置预览控件的相关属性
        self.preview.preview_size_combo = self.preview_size_combo
        self.preview.set_screen_type(
            self.screen_type_combo.currentText(),
            self.font_size_combo.currentText(),
            font_color=self.font_color_hex.text().strip() if hasattr(self,'font_color_hex') else "#FFFFFF",
            bg_color=self.bg_color_hex.text().strip() if hasattr(self,'bg_color_hex') else "#004080",
            selected_bg=self.selected_bg_hex.text().strip() if hasattr(self,'selected_bg_hex') else "#FFFFFF",
            selected_font=self.selected_font_hex.text().strip() if hasattr(self,'selected_font_hex') else "#000000",
            font_family=self.default_font_combo.currentText() if hasattr(self,'default_font_combo') else "Segoe UI"
        )
        self.preview.menu_root = self.menu_root
        self.preview.render_menu()
        
        # 连接屏幕类型切换信号，用于动态显示/隐藏颜色配置
        self.screen_type_combo.currentTextChanged.connect(self.on_screen_type_changed)
        # 初始化一次颜色配置可见性
        self.on_screen_type_changed()
        
        # 初始状态：保持颜色配置可见，由模式切换逻辑统一控制

    # ---------------- 配置处理方法 ----------------
    def on_screen_type_changed(self):
        """屏幕类型改变时更新配置，保存当前设置"""
        screen_type = self.screen_type_combo.currentText()
        
        # 根据屏幕类型显示或隐藏颜色配置
        if hasattr(self, 'color_group'):
            if screen_type == "OLED":
                self.color_group.setVisible(False)
                self.color_group.setEnabled(False)
            else:
                self.color_group.setVisible(True)
                self.color_group.setEnabled(True)
                try:
                    self.color_group.show()
                    self.color_group.update()
                except:
                    pass
        
        # 根据屏幕类型设置默认参数，但保留用户的自定义设置
        # 颜色模式选项已移除，不做颜色模式切换
        
        # 更新预览
        self.on_screen_config_changed()
        self.save_settings()
    
    def on_screen_config_changed(self):
        """屏幕配置改变时更新预览"""
        # 确保预览大小控件已传递
        self.preview.preview_size_combo = self.preview_size_combo
        
        # 获取颜色设置：优先使用 HEX 输入；若无，则使用预览当前颜色
        font_color = self.font_color_hex.text().strip() if hasattr(self, 'font_color_hex') else getattr(self.preview, 'fg_color', QColor(255,255,255)).name().upper()
        bg_color = self.bg_color_hex.text().strip() if hasattr(self, 'bg_color_hex') else getattr(self.preview, 'bg_color', QColor(0,64,128)).name().upper()
        selected_bg = self.selected_bg_hex.text().strip() if hasattr(self, 'selected_bg_hex') else getattr(self.preview, 'selected_bg_color', QColor(255,255,255)).name().upper()
        selected_font = self.selected_font_hex.text().strip() if hasattr(self, 'selected_font_hex') else getattr(self.preview, 'selected_fg_color', QColor(0,0,0)).name().upper()
        
        # 规范化HEX值
        if not font_color or not font_color.startswith('#'):
            font_color = QColor(255,255,255).name().upper()
        if not bg_color or not bg_color.startswith('#'):
            bg_color = QColor(0,64,128).name().upper()
        if not selected_bg or not selected_bg.startswith('#'):
            selected_bg = QColor(255,255,255).name().upper()
        if not selected_font or not selected_font.startswith('#'):
            selected_font = QColor(0,0,0).name().upper()
        
        # 传递所有颜色参数
        self.preview.set_screen_type(
            self.screen_type_combo.currentText(),
            self.font_size_combo.currentText(),
            font_color,
            bg_color,
            selected_bg,
            selected_font,
            font_family=self.default_font_combo.currentText() if hasattr(self,'default_font_combo') else "Segoe UI"
        )
        self.preview.render_menu()
    
    def on_preview_size_changed(self):
        """预览大小改变时更新显示"""
        # 将预览大小设置传递给预览控件
        self.preview.preview_size_combo = self.preview_size_combo
        self.preview.update_preview_size()
        self.preview.render_menu()
    
    def on_apply_screen_size(self):
        """应用用户自定义的屏幕尺寸"""
        try:
            width = int(self.screen_width_edit.text())
            height = int(self.screen_height_edit.text())
            
            # 限制屏幕尺寸范围
            width = max(64, min(width, 800))
            height = max(64, min(height, 800))
            
            # 更新预览控件的屏幕尺寸
            screen_type = self.screen_type_combo.currentText()
            # 已移除颜色模式选项
            font_size = self.font_size_combo.currentText()
            
            # 更新预览屏幕尺寸
            self.preview.fb_w = width
            self.preview.fb_h = height
            
            # 重新创建framebuffer
            self.preview.framebuffer = QPixmap(width, height)
            
            # 保留现有颜色设置，避免在TFT模式下清除用户选择
            if "OLED" in screen_type:
                # OLED：不重置颜色，沿用当前设置
                pass
            else:
                # TFT：从HEX输入框读取颜色（若有效），否则保持现有值
                def pick_hex(text, fallback):
                    try:
                        s = text.strip()
                        c = QColor(s)
                        return c if s.startswith('#') and c.isValid() else fallback
                    except:
                        return fallback
                if hasattr(self, 'bg_color_hex'):
                    self.preview.bg_color = pick_hex(self.bg_color_hex.text(), getattr(self.preview, 'bg_color', QColor(0,64,128)))
                if hasattr(self, 'font_color_hex'):
                    self.preview.fg_color = pick_hex(self.font_color_hex.text(), getattr(self.preview, 'fg_color', Qt.white))
                if hasattr(self, 'selected_bg_hex'):
                    self.preview.selected_bg_color = pick_hex(self.selected_bg_hex.text(), getattr(self.preview, 'selected_bg_color', QColor(255,255,255)))
                if hasattr(self, 'selected_font_hex'):
                    self.preview.selected_fg_color = pick_hex(self.selected_font_hex.text(), getattr(self.preview, 'selected_fg_color', Qt.black))
            
            self.preview.framebuffer.fill(self.preview.bg_color)
            
            # 根据高度调整最大行数
            self.preview.max_lines = max(8, height // 10)  # 假设每行10px高
            
            # 更新预览
            self.preview.update_preview_size()
            self.preview.render_menu()
            
            # 更新输入框中的值，确保显示的是实际应用的值
            self.screen_width_edit.setText(str(width))
            self.screen_height_edit.setText(str(height))
            
        except ValueError:
            # 处理无效输入
            self.screen_width_edit.setText(str(self.preview.fb_w))
            self.screen_height_edit.setText(str(self.preview.fb_h))
    
    def on_tab_changed(self, index):
        """选项卡切换时的处理"""
        pass  # 可以在这里添加选项卡切换时的特殊处理
    
    def toggle_color_config(self, show):
        """显示或隐藏颜色配置组"""
        # 查找颜色配置组
        if hasattr(self, 'tab_widget'):
            config_tab = self.tab_widget.widget(1)  # 第二个选项卡是配置
            if config_tab:
                # 查找颜色配置组
                for child in config_tab.findChildren(QGroupBox):
                    if child.title() == "颜色配置 (TFT模式)":
                        child.setVisible(show)

    def _parse_font_px(self):
        try:
            txt = self.font_size_combo.currentText()
            import re
            m = re.search(r"\((\d+)px\)", txt)
            return int(m.group(1)) if m else 12
        except:
            return 12

    def _render_glyph_bitmap(self, ch, family, px):
        from PySide6.QtGui import QImage, QFont
        img = QImage(px*2, px*2, QImage.Format_ARGB32)
        img.fill(Qt.black)
        f = QFont(family, px)
        p = QPainter(img)
        p.setPen(Qt.white)
        p.setFont(f)
        p.drawText(0, px, ch)
        p.end()
        w = min(img.width(), px*2)
        h = min(img.height(), px)
        data = []
        for y in range(h):
            byte = 0
            bit_count = 0
            for x in range(w):
                c = QColor(img.pixel(x,y))
                v = 1 if (c.red()+c.green()+c.blue())//3 > 128 else 0
                byte = (byte<<1) | v
                bit_count += 1
                if bit_count == 8:
                    data.append(byte)
                    byte = 0
                    bit_count = 0
            if bit_count:
                data.append(byte << (8-bit_count))
        return w, h, data

    def _emit_ascii_font_array(self):
        family = self.default_font_combo.currentText() if hasattr(self, 'default_font_combo') else 'Segoe UI'
        px = self._parse_font_px()
        lines = []
        lines.append("")
        lines.append(f"const uint8_t ascii_font_{px}[] = {{")
        for code in range(32,127):
            ch = chr(code)
            w,h,buf = self._render_glyph_bitmap(ch, family, px)
            lines.append(f"    /* {code} '{ch}' {w}x{h} */")
            for i in range(0,len(buf),16):
                part = ", ".join(f"0x{b:02X}" for b in buf[i:i+16])
                lines.append(f"    {part},")
        lines.append("};")
        return lines

    def _emit_ascii_font_full(self):
        family = self.default_font_combo.currentText() if hasattr(self, 'default_font_combo') else 'Segoe UI'
        px = self._parse_font_px()
        bitmap = []
        entries = []
        offset = 0
        for code in range(32,127):
            ch = chr(code)
            w,h,buf = self._render_glyph_bitmap(ch, family, px)
            entries.append((code, offset, w, h))
            bitmap.extend(buf)
            offset += len(buf)
        lines = []
        lines.append("")
        lines.append(f"const uint8_t ascii_bitmap_{px}[] = {{")
        for i in range(0, len(bitmap), 16):
            part = ", ".join(f"0x{b:02X}" for b in bitmap[i:i+16])
            lines.append(f"    {part},")
        lines.append("};")
        lines.append("")
        lines.append("typedef struct { uint16_t code; uint32_t offset; uint8_t w; uint8_t h; } AsciiGlyph;")
        lines.append(f"const AsciiGlyph ascii_table_{px}[] = {{")
        for code,off,w,h in entries:
            lines.append(f"    {{0x{code:02X}, {off}, {w}, {h}}},")
        lines.append("};")
        return lines

    def _collect_menu_chars(self):
        s = set()
        def walk(n):
            s.update(list(n.name))
            for c in n.children:
                walk(c)
        if self.menu_root:
            walk(self.menu_root)
        return s

    def _emit_cjk_font_subset(self):
        fam = self.default_font_combo.currentText() if hasattr(self, 'default_font_combo') else 'Microsoft YaHei'
        px = self._parse_font_px()
        used = sorted(self._collect_menu_chars())
        cjk = [ch for ch in used if ('\u4e00' <= ch <= '\u9fff') or ('\u3000' <= ch <= '\u303f')]
        if not cjk:
            return []
        bitmap = []
        entries = []
        offset = 0
        for ch in cjk:
            w,h,buf = self._render_glyph_bitmap(ch, fam, px)
            entries.append((ord(ch), offset, w, h))
            bitmap.extend(buf)
            offset += len(buf)
        lines = []
        lines.append("")
        lines.append(f"const uint8_t cjk_bitmap_{px}[] = {{")
        for i in range(0, len(bitmap), 16):
            part = ", ".join(f"0x{b:02X}" for b in bitmap[i:i+16])
            lines.append(f"    {part},")
        lines.append("};")
        lines.append("")
        lines.append("typedef struct { uint16_t code; uint32_t offset; uint8_t w; uint8_t h; } GlyphEntry;")
        lines.append(f"const GlyphEntry cjk_table_{px}[] = {{")
        for code,off,w,h in entries:
            lines.append(f"    {{0x{code:04X}, {off}, {w}, {h}}},")
        lines.append("};")
        return lines
        
    # ---------------- 颜色选择器方法 ----------------
    def filter_menu_tree(self):
        query = self.menu_search_edit.text().strip().lower() if hasattr(self, 'menu_search_edit') else ""
        def recurse(item):
            from PySide6.QtGui import QFont, QBrush
            match = (query in item.text(0).lower()) if query else True
            child_visible = False
            for i in range(item.childCount()):
                c = item.child(i)
                child_vis = recurse(c)
                child_visible = child_visible or child_vis
            visible = match or child_visible
            item.setHidden(not visible)
            f = item.font(0)
            f.setBold(match and query != "")
            item.setFont(0, f)
            item.setForeground(0, QBrush(QColor("#3DA9FC" if match and query != "" else "#e6e6e6")))
            return visible
        for i in range(self.tree.topLevelItemCount()):
            recurse(self.tree.topLevelItem(i))
        self.tree.expandAll()

    def _on_tree_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self.tree.itemAt(pos)
        menu = QMenu(self)
        act_add = menu.addAction("添加子菜单")
        act_del = menu.addAction("删除")
        act_rename = menu.addAction("重命名")
        act_toggle_exec = menu.addAction("切换执行/子菜单")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if not chosen:
            return
        if chosen == act_add:
            self.add_menu()
        elif chosen == act_del:
            self.del_menu()
        elif chosen == act_rename and item:
            self.tree.editItem(item, 0)
        elif chosen == act_toggle_exec:
            self.toggle_exec()
    def choose_color(self, color_type):
        """打开颜色选择器"""
        from PySide6.QtWidgets import QColorDialog
        
        # 设置合理的默认颜色
        defaults = {
            'bg': QColor(0, 64, 128),    # 深蓝色背景
            'font': QColor(255, 255, 255), # 白色文字
            'selected_bg': QColor(255, 255, 0), # 黄色选中背景
            'selected_font': QColor(0, 0, 0)   # 黑色选中文字
        }
        
        # 获取当前颜色
        if color_type == 'bg':
            current_color = getattr(self.preview, 'bg_color', defaults[color_type])
            btn = self.bg_color_btn
        elif color_type == 'font':
            current_color = getattr(self.preview, 'fg_color', defaults[color_type])
            btn = self.font_color_btn
        elif color_type == 'selected_bg':
            current_color = getattr(self.preview, 'selected_bg_color', defaults[color_type])
            btn = self.selected_bg_btn
        elif color_type == 'selected_font':
            current_color = getattr(self.preview, 'selected_fg_color', defaults[color_type])
            btn = self.selected_font_btn
        else:
            return
        
        # 打开颜色选择器
        color = QColorDialog.getColor(current_color, self, f"选择{color_type}颜色")
        if color.isValid():
            # 更新按钮颜色
            text_color = 'white' if color.lightness() < 128 else 'black'
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {text_color};
                    border: 2px solid #555555;
                    border-radius: 6px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    border-color: #0078d4;
                }}
                QPushButton:pressed {{
                    background-color: {color.darker(120).name()};
                }}
            """)

            # 根据选择的颜色类型更新预览控件
            if color_type == 'bg':
                self.preview.bg_color = color
            elif color_type == 'font':
                self.preview.fg_color = color
            elif color_type == 'selected_bg':
                self.preview.selected_bg_color = color
            elif color_type == 'selected_font':
                self.preview.selected_fg_color = color
            
            # 重新渲染预览
            self.preview.render_menu()
            self.save_settings()
            self.save_settings()
            
            # 重新渲染预览
            self.preview.render_menu()
    
    def on_hex_color_changed(self):
        """处理HEX颜色输入变化"""
        sender = self.sender()
        if not sender:
            return
            
        hex_color = sender.text().strip()
        if not hex_color.startswith('#'):
            return
            
        try:
            # 解析HEX颜色
            color = QColor(hex_color)
            if not color.isValid():
                return
                
            # 根据发送者确定颜色类型并更新
            if sender == self.bg_color_hex:
                self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
            elif sender == self.font_color_hex:
                self.font_color_btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
            elif sender == self.selected_bg_hex:
                self.selected_bg_btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
            elif sender == self.selected_font_hex:
                self.selected_font_btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
        
            self.on_screen_config_changed()
            self.save_settings()
        except:
            pass  # 忽略无效的HEX输入
    
    # ---------------- 设置保存和加载 ----------------
    def save_settings(self):
        """保存当前设置到文件"""
        import json
        import os
        
        settings = {
            'screen_type': self.screen_type_combo.currentText(),
            'font_size': self.font_size_combo.currentText(),
            'preview_size': self.preview_size_combo.currentText(),
            'bg_color': self.bg_color_hex.text().strip() if hasattr(self, 'bg_color_hex') else getattr(self.preview, 'bg_color', QColor(0,64,128)).name().upper(),
            'font_color': self.font_color_hex.text().strip() if hasattr(self, 'font_color_hex') else getattr(self.preview, 'fg_color', QColor(255,255,255)).name().upper(),
            'selected_bg': self.selected_bg_hex.text().strip() if hasattr(self, 'selected_bg_hex') else getattr(self.preview, 'selected_bg_color', QColor(255,255,255)).name().upper(),
            'selected_font': self.selected_font_hex.text().strip() if hasattr(self, 'selected_font_hex') else getattr(self.preview, 'selected_fg_color', QColor(0,0,0)).name().upper(),
            'font_family': self.default_font_combo.currentText() if hasattr(self, 'default_font_combo') else 'Segoe UI',
            'emit_font_array': self.cb_emit_font.isChecked() if hasattr(self, 'cb_emit_font') else True,
            'emit_draw_skeleton': self.cb_emit_draw.isChecked() if hasattr(self, 'cb_emit_draw') else True,
            'emit_cjk_subset': self.cb_emit_cjk.isChecked() if hasattr(self, 'cb_emit_cjk') else True,
            'export_no_u8g2': self.cb_no_u8g2.isChecked() if hasattr(self, 'cb_no_u8g2') else False,
            'screen_width': self.screen_width_edit.text(),
            'screen_height': self.screen_height_edit.text(),
            'menu_data': self.serialize_menu()  # 保存菜单数据
        }
        
        try:
            settings_file = os.path.join(os.path.dirname(__file__), 'menu_designer_settings.json')
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存设置失败: {e}")
    
    def load_settings(self):
        """从文件加载设置"""
        import json
        import os
        
        settings_file = os.path.join(os.path.dirname(__file__), 'menu_designer_settings.json')
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.current_settings.update(settings)
            except Exception as e:
                print(f"加载设置失败: {e}")
    
    def apply_loaded_settings(self):
        """应用加载的设置到界面"""
        try:
            # 使用更长的延迟，确保所有控件都完全创建
            def delayed_apply():
                try:
                    # 再延迟一次，确保UI完全初始化
                    def final_apply():
                        try:
                            print(f"应用设置: {self.current_settings}")
                            
                            # 检查是否有菜单数据需要恢复
                            if 'menu_data' in self.current_settings and self.current_settings['menu_data']:
                                # 恢复菜单数据
                                restored_root = self.deserialize_menu(self.current_settings['menu_data'])
                                if restored_root:
                                    self.menu_root = restored_root
                                    self.refresh_tree()
                                    print("菜单数据已恢复")
                            
                            # 应用屏幕类型
                            if hasattr(self, 'screen_type_combo') and 'screen_type' in self.current_settings:
                                self.screen_type_combo.blockSignals(True)  # 阻止信号
                                self.screen_type_combo.setCurrentText(self.current_settings['screen_type'])
                                self.screen_type_combo.blockSignals(False)
                                print(f"设置屏幕类型: {self.current_settings['screen_type']}")
                                try:
                                    self.on_screen_type_changed()
                                except:
                                    pass
                            
                            # 颜色模式已移除
                            
                            # 应用字体大小
                            if hasattr(self, 'font_size_combo') and 'font_size' in self.current_settings:
                                self.font_size_combo.blockSignals(True)
                                self.font_size_combo.setCurrentText(self.current_settings['font_size'])
                                self.font_size_combo.blockSignals(False)
                                print(f"设置字体大小: {self.current_settings['font_size']}")
                            
                            # 应用预览大小
                            if hasattr(self, 'preview_size_combo') and 'preview_size' in self.current_settings:
                                self.preview_size_combo.blockSignals(True)
                                self.preview_size_combo.setCurrentText(self.current_settings['preview_size'])
                                self.preview_size_combo.blockSignals(False)
                                print(f"设置预览大小: {self.current_settings['preview_size']}")
                            
                            # 应用字体族
                            if hasattr(self, 'default_font_combo') and 'font_family' in self.current_settings:
                                try:
                                    self.default_font_combo.blockSignals(True)
                                    self.default_font_combo.setCurrentText(self.current_settings['font_family'])
                                    self.default_font_combo.blockSignals(False)
                                    print(f"设置默认字体: {self.current_settings['font_family']}")
                                except:
                                    pass
                            # 应用代码生成选项
                            if hasattr(self, 'cb_emit_font') and 'emit_font_array' in self.current_settings:
                                self.cb_emit_font.blockSignals(True)
                                self.cb_emit_font.setChecked(bool(self.current_settings['emit_font_array']))
                                self.cb_emit_font.blockSignals(False)
                            if hasattr(self, 'cb_emit_draw') and 'emit_draw_skeleton' in self.current_settings:
                                self.cb_emit_draw.blockSignals(True)
                                self.cb_emit_draw.setChecked(bool(self.current_settings['emit_draw_skeleton']))
                                self.cb_emit_draw.blockSignals(False)
                            if hasattr(self, 'cb_emit_cjk') and 'emit_cjk_subset' in self.current_settings:
                                self.cb_emit_cjk.blockSignals(True)
                                self.cb_emit_cjk.setChecked(bool(self.current_settings['emit_cjk_subset']))
                                self.cb_emit_cjk.blockSignals(False)
                            if hasattr(self, 'cb_no_u8g2') and 'export_no_u8g2' in self.current_settings:
                                self.cb_no_u8g2.blockSignals(True)
                                self.cb_no_u8g2.setChecked(bool(self.current_settings['export_no_u8g2']))
                                self.cb_no_u8g2.blockSignals(False)
                            
                            # 应用屏幕尺寸
                            if hasattr(self, 'screen_width_edit') and 'screen_height_edit' and 'screen_width' in self.current_settings and 'screen_height' in self.current_settings:
                                self.screen_width_edit.blockSignals(True)
                                self.screen_height_edit.blockSignals(True)
                                self.screen_width_edit.setText(self.current_settings['screen_width'])
                                self.screen_height_edit.setText(self.current_settings['screen_height'])
                                self.screen_width_edit.blockSignals(False)
                                self.screen_height_edit.blockSignals(False)
                                
                                # 实际应用屏幕尺寸设置到预览控件
                                try:
                                    self.on_apply_screen_size()
                                    print(f"应用屏幕尺寸: {self.current_settings['screen_width']}x{self.current_settings['screen_height']}")
                                except Exception as e:
                                    print(f"应用屏幕尺寸失败: {e}")
                            
                            # 应用颜色设置（OLED和TFT模式都支持）
                            if hasattr(self, 'screen_type_combo'):
                                try:
                                    from PySide6.QtGui import QColor
                                    # 背景颜色
                                    if 'bg_color' in self.current_settings:
                                        c = QColor(self.current_settings['bg_color'])
                                        if c.isValid():
                                            self.preview.bg_color = c
                                            self.bg_color_btn.setStyleSheet(
                                                f"background-color: {c.name()}; color: {'white' if c.lightness() < 128 else 'black'};"
                                            )
                                    # 字体颜色
                                    if 'font_color' in self.current_settings:
                                        c = QColor(self.current_settings['font_color'])
                                        if c.isValid():
                                            self.preview.fg_color = c
                                            self.font_color_btn.setStyleSheet(
                                                f"background-color: {c.name()}; color: {'white' if c.lightness() < 128 else 'black'};"
                                            )
                                    # 选中背景
                                    if 'selected_bg' in self.current_settings:
                                        c = QColor(self.current_settings['selected_bg'])
                                        if c.isValid():
                                            self.preview.selected_bg_color = c
                                            self.selected_bg_btn.setStyleSheet(
                                                f"background-color: {c.name()}; color: {'white' if c.lightness() < 128 else 'black'};"
                                            )
                                    # 选中字体
                                    if 'selected_font' in self.current_settings:
                                        c = QColor(self.current_settings['selected_font'])
                                        if c.isValid():
                                            self.preview.selected_fg_color = c
                                            self.selected_font_btn.setStyleSheet(
                                                f"background-color: {c.name()}; color: {'white' if c.lightness() < 128 else 'black'};"
                                            )
                                except:
                                    pass
                            
                            # 更新预览
                            if hasattr(self, 'preview'):
                                self.preview.menu_root = self.menu_root
                                self.on_screen_config_changed()
                                print("预览已更新")
                            
                            print("所有设置应用完成")
                            
                        except Exception as e:
                            print(f"最终应用设置失败: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(200, final_apply)
                        
                except Exception as e:
                    print(f"延迟应用设置失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 使用QTimer延迟应用设置
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, delayed_apply)
            
        except Exception as e:
            print(f"应用设置失败: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """窗口关闭时保存设置"""
        self.save_settings()
        super().closeEvent(event)
    
    def serialize_menu(self):
        """序列化菜单数据为字典格式"""
        def serialize_node(node):
            return {
                'name': node.name,
                'is_exec': node.is_exec,
                'visible': node.visible,
                'callback_name': node.callback_name,
                'cursor_pos': node.cursor_pos,
                'children': [serialize_node(child) for child in node.children]
            }
        
        if self.menu_root:
            return serialize_node(self.menu_root)
        else:
            return None
    
    def deserialize_menu(self, menu_data):
        """从字典数据反序列化菜单数据"""
        def deserialize_node(data, parent=None):
            node = MenuItem(
                name=data.get('name', '菜单项'),
                is_exec=data.get('is_exec', False),
                visible=data.get('visible', True),
                parent=parent
            )
            node.callback_name = data.get('callback_name', '')
            node.cursor_pos = data.get('cursor_pos', 0)
            
            for child_data in data.get('children', []):
                child_node = deserialize_node(child_data, node)
                node.children.append(child_node)
            
            return node
        
        if menu_data:
            self.menu_root = deserialize_node(menu_data)
            return self.menu_root
        else:
            return None
        
    # ---------------- Tree操作 ----------------
    def refresh_tree(self):
        self.tree.clear()
        from PySide6.QtGui import QIcon, QPixmap, QPainter
        def make_dot(color_hex):
            pm = QPixmap(14,14)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setBrush(QColor(color_hex))
            p.setPen(Qt.NoPen)
            p.drawEllipse(2,2,10,10)
            p.end()
            return QIcon(pm)
        icon_exec = make_dot("#FFD54F")
        icon_folder = make_dot("#3DA9FC")
        def add_items(parent, node):
            label = node.name if not node.children else f"{node.name} ({len(node.children)})"
            info = (f"执行" + (f" · {node.callback_name}" if node.callback_name else "")) if node.is_exec else f"子菜单 {len(node.children)}"
            twi = QTreeWidgetItem([label, info])
            twi.setData(0, Qt.UserRole, node)
            twi.setToolTip(0, label)
            twi.setToolTip(1, info)
            twi.setIcon(0, icon_exec if node.is_exec else icon_folder)
            from PySide6.QtGui import QBrush
            twi.setForeground(1, QBrush(QColor("#FFD54F" if node.is_exec else "#3DA9FC")))
            if parent:
                parent.addChild(twi)
            else:
                self.tree.addTopLevelItem(twi)
            for c in node.children:
                add_items(twi,c)
        add_items(None,self.menu_root)
        self.tree.expandAll()

    def on_tree_select(self,item):
        node = item.data(0, Qt.UserRole)
        self.current_node = node
        # 更新面包屑
        path_names = []
        p = node
        while p:
            path_names.insert(0, p.name)
            p = p.parent
        self.menu_breadcrumb.setText(" / ".join(path_names))
        
        # 显示属性编辑区域
        self.properties_widget.setVisible(True)
        self.selection_label.setVisible(False)
        
        # 计算菜单项层级
        depth = 0
        parent = node.parent
        while parent and parent != self.menu_root:
            depth += 1
            parent = parent.parent
        
        # 更新当前选中项信息标签
        menu_type = "执行项" if node.is_exec else "子菜单"
        self.current_item_label.setText(f"当前选中: {node.name} ({menu_type}, 第{depth+1}层)")
        
        # 显示选中菜单项的名称
        self.name_edit.setText(node.name)
        
        # 显示选中菜单项的回调函数（如果是执行项）
        if node.is_exec:
            self.callback_edit.setText(node.callback_name)
            self.callback_edit.setEnabled(True)
            self.callback_edit.setPlaceholderText("请输入回调函数名")
        else:
            self.callback_edit.setText("")
            self.callback_edit.setEnabled(False)
            self.callback_edit.setPlaceholderText("(子菜单项，无需回调函数)")

    def update_name(self):
        if self.current_node:
            self.current_node.name = self.name_edit.text()
            self.refresh_tree()
            self.preview.render_menu()

    def update_callback(self):
        if self.current_node and self.current_node.is_exec:
            self.current_node.callback_name = self.callback_edit.text()

    def toggle_exec(self):
        if self.current_node:
            self.current_node.is_exec = not self.current_node.is_exec
            # 检查并设置叶子节点为执行项
            self.current_node.check_and_set_leaf_nodes_exec()
            self.refresh_tree()
            self.preview.render_menu()

    def add_menu(self):
        if self.current_node:
            new_node = MenuItem("新菜单", is_exec=False)  # 默认创建子菜单，不是执行项
            self.current_node.add_child(new_node)
            self.refresh_tree()
            # 自动选中新创建的子菜单项
            self.current_node = new_node
            self.preview.render_menu()
            # 更新属性面板
            self.name_edit.setText(new_node.name)
            self.callback_edit.setText(new_node.callback_name)

    def del_menu(self):
        if self.current_node and self.current_node.parent:
            self.current_node.parent.children.remove(self.current_node)
            self.current_node = self.current_node.parent
            self.refresh_tree()
            self.preview.render_menu()

    def on_key(self, key):
        # 防抖处理：如果正在处理按键，则忽略新的按键
        if self.key_processing:
            return
            
        # 如果已有防抖定时器，则停止它
        if self.key_debounce_timer:
            self.key_debounce_timer.stop()
            
        # 设置处理标志
        self.key_processing = True
        
        # 使用定时器延迟处理按键，防止快速按键导致的状态混乱
        self.key_debounce_timer = QTimer.singleShot(50, lambda: self._process_key(key))
    
    def _process_key(self, key):
        """实际处理按键的函数"""
        try:
            timestamp = f"[{QTime.currentTime().toString('hh:mm:ss')}]"
            debug_info = ""
            
            # 处理右键按下 - 进入子菜单或执行
            if key == "Right":
                visible = [c for c in self.preview.menu_root.children if c.visible]
                if 0 <= self.preview.cursor_index < len(visible):
                    node = visible[self.preview.cursor_index]
                    if node.is_exec:
                        # 执行项
                        debug_info = f"{timestamp} 按键: Right → 执行回调函数: {node.callback_name or '(未命名)'}"
                        # 实际执行回调函数
                        if node.callback_name:
                            # 查找并执行回调函数
                            if hasattr(self, node.callback_name) and callable(getattr(self, node.callback_name)):
                                getattr(self, node.callback_name)()
                            else:
                                debug_info += f" (警告: 回调函数 {node.callback_name} 未定义)"
                    elif node.children and len(node.children) > 0:
                        # 进入子菜单 - 先更新状态，再生成调试信息
                        old_menu = self.preview.menu_root.name
                        self.preview.menu_root = node
                        self.preview.cursor_index = 0  # 重置到第一项
                        debug_info = f"{timestamp} 按键: Right → 进入子菜单: {node.name} (包含{len(node.children)}个子项)"
                    else:
                        debug_info = f"{timestamp} 按键: Right → 该菜单项[{node.name}]没有子菜单"
                else:
                    debug_info = f"{timestamp} 按键: Right → 无效位置"
            
            # 处理左键按下 - 返回上级菜单
            elif key == "Left":
                if self.preview.menu_root.parent:
                    # 保存当前菜单项的位置
                    current_root = self.preview.menu_root
                    current_root.cursor_pos = self.preview.cursor_index
                    
                    # 返回上级菜单 - 先更新状态，再生成调试信息
                    old_menu = self.preview.menu_root.name
                    self.preview.menu_root = self.preview.menu_root.parent
                    
                    # 在父菜单中找到当前子菜单的位置
                    parent_visible = [c for c in self.preview.menu_root.children if c.visible]
                    for i, child in enumerate(parent_visible):
                        if child == current_root:
                            # 尝试恢复之前保存的位置
                            if hasattr(child, 'cursor_pos'):
                                self.preview.cursor_index = min(child.cursor_pos, len(parent_visible) - 1)
                            else:
                                self.preview.cursor_index = i
                            break
                    else:
                        self.preview.cursor_index = 0
                    
                    new_item_name = parent_visible[self.preview.cursor_index].name if 0 <= self.preview.cursor_index < len(parent_visible) else "未知"
                    debug_info = f"{timestamp} 按键: Left → 返回上级菜单: {self.preview.menu_root.name} (当前位置: {new_item_name})"
                else:
                    debug_info = f"{timestamp} 按键: Left → 已在根菜单，无法返回"
            
            # 处理上下键 - 导航菜单项
            elif key in ["Up", "Down"]:
                visible = [c for c in self.preview.menu_root.children if c.visible]
                
                # 检查是否有可见菜单项
                if not visible:
                    debug_info = f"{timestamp} 按键: {key} → 没有可见菜单项"
                else:
                    # 确保cursor_index在有效范围内
                    if self.preview.cursor_index < 0:
                        self.preview.cursor_index = 0
                    elif self.preview.cursor_index >= len(visible):
                        self.preview.cursor_index = len(visible) - 1
                    
                    # 获取当前菜单项名称
                    old_index = self.preview.cursor_index
                    old_item_name = visible[old_index].name if 0 <= old_index < len(visible) else "未知"
                    
                    # 处理按键
                    if key == "Up":
                        # 检查是否已经在第一项
                        if old_index == 0:
                            # 已经在第一项，无法上移
                            debug_info = f"{timestamp} 按键: {key} → 已在第一项 [{old_item_name}]，无法上移"
                        else:
                            # 可以上移，先更新状态，再生成调试信息
                            new_index = old_index - 1
                            self.preview.cursor_index = new_index
                            new_item_name = visible[new_index].name if 0 <= new_index < len(visible) else "未知"
                            debug_info = f"{timestamp} 按键: {key} → 从[{old_item_name}]({old_index}) 移动到 [{new_item_name}]({new_index})"
                    elif key == "Down":
                        # 检查是否已经在最后一项
                        if old_index == len(visible) - 1:
                            # 已经在最后一项，无法下移
                            debug_info = f"{timestamp} 按键: {key} → 已在最后一项 [{old_item_name}]，无法下移"
                        else:
                            # 可以下移，先更新状态，再生成调试信息
                            new_index = old_index + 1
                            self.preview.cursor_index = new_index
                            new_item_name = visible[new_index].name if 0 <= new_index < len(visible) else "未知"
                            debug_info = f"{timestamp} 按键: {key} → 从[{old_item_name}]({old_index}) 移动到 [{new_item_name}]({new_index})"
                    
                    # 保存当前菜单项的位置
                    self.preview.menu_root.cursor_pos = self.preview.cursor_index
            else:
                debug_info = f"{timestamp} 按键: {key} → 未知按键"
            
            # 打印调试信息 - 在所有状态更新后
            print(debug_info)
            
            # 更新调试信息显示
            if hasattr(self, 'debug_text') and debug_info:
                # 获取当前调试信息
                current_text = self.debug_text.toPlainText()
                if current_text == "等待按键操作...":
                    new_text = debug_info
                else:
                    # 保留最近的20条记录
                    lines = current_text.split('\n')
                    lines.append(debug_info)
                    if len(lines) > 20:
                        lines = lines[-20:]
                    new_text = '\n'.join(lines)
                
                
            
            # 重新渲染菜单 - 在所有状态更新和调试信息更新后
            self.preview.render_menu()
            
        except Exception as e:
            # 捕获异常，防止按键处理崩溃
            timestamp = f"[{QTime.currentTime().toString('hh:mm:ss')}]"
            error_msg = f"{timestamp} 按键处理错误: {str(e)}"
            print(error_msg)
            
            # 即使出错也要更新调试信息
            if hasattr(self, 'debug_text'):
                # 获取当前调试信息
                current_text = self.debug_text.toPlainText()
                if current_text == "等待按键操作...":
                    new_text = error_msg
                else:
                    # 保留最近的20条记录
                    lines = current_text.split('\n')
                    lines.append(error_msg)
                    if len(lines) > 20:
                        lines = lines[-20:]
                    new_text = '\n'.join(lines)
                
                
        finally:
            # 重置处理标志
            self.key_processing = False

    def apply_modern_style(self):
        """应用现代化样式表"""
        modern_style = """        /* 现代化样式表 - 增强版深色主题 */
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            font-size: 9pt;
        }
        
        QMainWindow, QDialog {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1e1e1e, stop:1 #252525);
            border: 1px solid #404040;
        }
        
        /* 按钮样式 - 现代化设计 */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3a3a3a, stop:1 #2d2d2d);
            color: #ffffff;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 9pt;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a4a4a, stop:1 #3d3d3d);
            border-color: #0078d4;
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2a2a2a, stop:1 #1d1d1d);
            border-color: #005a9e;
        }
        
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #666666;
            border-color: #404040;
        }
        
        /* 主要操作按钮样式 */
        QPushButton[class="primary"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0078d4, stop:1 #005a9e);
            border-color: #0078d4;
            font-weight: 600;
        }
        
        QPushButton[class="primary"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #106ebe, stop:1 #004578);
        }
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 2px solid #404040;
            border-radius: 6px;
            padding: 6px 12px;
            selection-background-color: #0078d4;
            font-size: 9pt;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #0078d4;
            background-color: #333333;
        }
        
        /* 下拉框样式 */
        QComboBox {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 2px solid #404040;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 9pt;
            min-height: 20px;
        }
        
        QComboBox:hover {
            border-color: #555555;
        }
        
        QComboBox:focus {
            border-color: #0078d4;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 24px;
            background: transparent;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid #e0e0e0;
            width: 0;
            height: 0;
        }
        
        QComboBox QAbstractItemView {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 2px solid #404040;
            border-radius: 6px;
            selection-background-color: #0078d4;
            selection-color: #ffffff;
            padding: 4px;
        }
        
        QComboBox QAbstractItemView::item {
            padding: 6px 12px;
            border-radius: 4px;
            margin: 2px;
        }
        
        QComboBox QAbstractItemView::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        
        QComboBox QAbstractItemView::item:hover {
            background-color: #404040;
        }
        
        /* 树控件样式 - 增强版 */
        QTreeWidget {
            background-color: #252525;
            color: #ffffff;
            border: 2px solid #0078d4;
            border-radius: 8px;
            alternate-background-color: #2a2a2a;
            font-size: 10pt;
            font-weight: 500;
            gridline-color: #404040;
            outline: none;
            selection-background-color: transparent;
        }
        
        QTreeWidget::header {
            background-color: #1e3a5f;
            color: #ffffff;
            border: none;
            border-bottom: 2px solid #0078d4;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 12px;
            font-size: 11pt;
            font-weight: 600;
            min-height: 32px;
        }
        
        QTreeWidget::item {
            padding: 8px 12px;
            border: none;
            min-height: 28px;
            border-bottom: 1px solid #333333;
            margin: 0px;
        }
        
        QTreeWidget::item:selected {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0078d4, stop:0.5 #0099ff, stop:1 #0078d4);
            color: #ffffff;
            border-radius: 4px;
            border: 1px solid #005a9e;
            font-weight: 600;
        }
        
        QTreeWidget::item:hover:selected {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #106ebe, stop:0.5 #1aa0ff, stop:1 #106ebe);
            border-color: #0078d4;
        }
        
        QTreeWidget::item:hover:!selected {
            background-color: #404040;
            color: #ffffff;
            border-radius: 4px;
            border: 1px solid #555555;
        }
        
        QTreeWidget::branch {
            background: transparent;
            border: none;
        }
        
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {
            image: none;
            border: 2px solid #0078d4;
            border-radius: 2px;
            width: 12px;
            height: 12px;
            background-color: #2d2d2d;
        }
        
        QTreeWidget::branch:has-children:!has-siblings:open,
        QTreeWidget::branch:open:has-children:has-siblings {
            image: none;
            border: 2px solid #0078d4;
            border-radius: 2px;
            width: 12px;
            height: 12px;
            background-color: #0078d4;
        }
        
        QTreeWidget::branch:has-children:has-siblings:closed,
        QTreeWidget::branch:has-siblings:closed {
            image: none;
            border: 2px solid #0078d4;
            border-radius: 2px;
            width: 12px;
            height: 12px;
            background-color: #2d2d2d;
        }
        
        QTreeWidget::branch:has-children:has-siblings:open,
        QTreeWidget::branch:has-siblings:open {
            image: none;
            border: 2px solid #0078d4;
            border-radius: 2px;
            width: 12px;
            height: 12px;
            background-color: #0078d4;
        }
        
        QTreeWidget::branch:has-children:!has-siblings:closed:hover,
        QTreeWidget::branch:closed:has-children:has-siblings:hover,
        QTreeWidget::branch:has-children:has-siblings:closed:hover,
        QTreeWidget::branch:has-siblings:closed:hover {
            border-color: #0099ff;
            background-color: #404040;
        }
        
        QTreeWidget::branch:has-children:!has-siblings:open:hover,
        QTreeWidget::branch:open:has-children:has-siblings:hover,
        QTreeWidget::branch:has-children:has-siblings:open:hover,
        QTreeWidget::branch:has-siblings:open:hover {
            border-color: #0099ff;
        }
        
        QTreeWidget::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid #0078d4;
            background-color: #2d2d2d;
            margin: 2px;
        }
        
        QTreeWidget::indicator:hover {
            border-color: #0099ff;
            background-color: #404040;
        }
        
        QTreeWidget::indicator:checked {
            background-color: #0078d4;
            border-color: #0078d4;
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEgNkw1IDEwTDExIDIiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
        }
        
        QTreeWidget::indicator:checked:hover {
            background-color: #0099ff;
            border-color: #0099ff;
        }
        
        /* 分组框样式 */
        QGroupBox {
            background-color: #252525;
            color: #e0e0e0;
            border: 2px solid #404040;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 16px;
            font-weight: 600;
            font-size: 10pt;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 12px;
            background-color: #252525;
            border-radius: 4px;
            left: 12px;
        }
        
        /* 标签样式 */
        QLabel {
            color: #e0e0e0;
            background: transparent;
            font-size: 9pt;
            font-weight: 500;
        }
        
        QLabel[class="heading"] {
            font-size: 11pt;
            font-weight: 600;
            color: #0078d4;
            margin: 8px 0;
        }
        
        QLabel[class="description"] {
            color: #a0a0a0;
            font-size: 8pt;
            font-style: italic;
        }
        
        /* 滚动条样式 */
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 14px;
            margin: 0px;
            border-radius: 7px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 7px;
            min-height: 30px;
            border: none;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QScrollBar::handle:vertical:pressed {
            background-color: #0078d4;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #2d2d2d;
            height: 14px;
            margin: 0px;
            border-radius: 7px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #555555;
            border-radius: 7px;
            min-width: 30px;
            border: none;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #666666;
        }
        
        QScrollBar::handle:horizontal:pressed {
            background-color: #0078d4;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
            width: 0px;
        }
        
        /* 工具提示样式 */
        QToolTip {
            background-color: #333333;
            color: #e0e0e0;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 8pt;
        }
        
        /* 菜单样式 */
        QMenuBar {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border-bottom: 2px solid #404040;
        }
        
        QMenuBar::item {
            padding: 6px 12px;
            background: transparent;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #0078d4;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 2px solid #404040;
            border-radius: 6px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 6px 20px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #0078d4;
            color: #ffffff;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #404040;
            margin: 4px 12px;
        }
        
        /* 状态栏样式 */
        QStatusBar {
            background-color: #2d2d2d;
            color: #a0a0a0;
            border-top: 1px solid #404040;
        }
        
        /* 进度条样式 */
        QProgressBar {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 6px;
            text-align: center;
            color: #ffffff;
            font-weight: 500;
        }
        
        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 4px;
        }
        
        /* 选项卡样式 */
        QTabWidget::pane {
            border: 2px solid #404040;
            background-color: #1e1e1e;
            border-radius: 6px;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #a0a0a0;
            padding: 8px 16px;
            border: none;
            border-bottom: 3px solid transparent;
            margin-right: 2px;
            font-weight: 500;
        }
        
        QTabBar::tab:selected {
            background-color: #1e1e1e;
            border-bottom: 3px solid #0078d4;
            color: #e0e0e0;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #3a3a3a;
            color: #e0e0e0;
        }
        
        /* 复选框样式 */
        QCheckBox {
            color: #e0e0e0;
            font-size: 9pt;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid #555555;
            background-color: #2d2d2d;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border-color: #0078d4;
        }
        
        QCheckBox::indicator:hover {
            border-color: #0078d4;
        }
        
        /* 单选按钮样式 */
        QRadioButton {
            color: #e0e0e0;
            font-size: 9pt;
            spacing: 8px;
        }
        
        QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid #555555;
            background-color: #2d2d2d;
        }
        
        QRadioButton::indicator:checked {
            background-color: #0078d4;
            border-color: #0078d4;
        }
        
        QRadioButton::indicator:checked::after {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 3px;
            background-color: white;
            position: absolute;
            top: 6px;
            left: 6px;
        }
        
        QRadioButton::indicator:hover {
            border-color: #0078d4;
        }
        
        /* 颜色选择按钮特殊样式 */
        QPushButton[class="color-btn"] {
            min-width: 80px;
            max-width: 80px;
            padding: 4px;
            border-radius: 4px;
            font-size: 8pt;
        }
        
        /* 按键按钮样式 */
        QPushButton[class="key-btn"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a4a4a, stop:1 #3d3d3d);
            border: 2px solid #606060;
            border-radius: 8px;
            font-weight: 600;
            font-size: 10pt;
            min-width: 60px;
            min-height: 35px;
        }
        
        QPushButton[class="key-btn"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #5a5a5a, stop:1 #4d4d4d);
            border-color: #0078d4;
        }
        
        QPushButton[class="key-btn"]:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3a3a3a, stop:1 #2d2d2d);
        }
        """
        
        self.setStyleSheet(modern_style)

    # ---------------- 导出完整 C 代码 ----------------
    def export_code(self):
        import os
        out_dir = QFileDialog.getExistingDirectory(self, "选择导出目录", "")
        if not out_dir:
            return
        px = self._parse_font_px()
        def _sanitize_ident(s, fallback):
            import re
            ident = re.sub(r"[^A-Za-z0-9_]", "_", s)
            ident = re.sub(r"_+", "_", ident).strip("_")
            if not ident or ident[0].isdigit():
                ident = fallback
            return ident
        menu_h = []
        menu_h.append("#ifndef MENU_H")
        menu_h.append("#define MENU_H")
        menu_h.append("#include <u8g2.h>")
        menu_h.append("#include <stdint.h>")
        menu_h.append("typedef struct MenuItem {")
        menu_h.append("  const char *name;")
        menu_h.append("  uint8_t is_exec;")
        menu_h.append("  uint8_t child_count;")
        menu_h.append("  struct MenuItem *children;")
        menu_h.append("  void (*callback)(void);")
        menu_h.append("} MenuItem;")
        menu_h.append("extern MenuItem *menu_root;")
        menu_h.append("void draw_menu(u8g2_t *u8g2, MenuItem *root, uint8_t cursor, uint8_t view_start);")
        menu_h.append("#endif")

        menu_c = []
        menu_c.append("#include \"menu.h\"")
        if hasattr(self, 'cb_emit_cjk') and self.cb_emit_cjk.isChecked():
            menu_c.append("#include \"../fonts/cjk_font.h\"")
        menu_c.append("#include \"../callbacks/callbacks.h\"")
        menu_c.append("")
        callbacks_h = []
        callbacks_c = []
        callbacks_h.append("#ifndef MENU_CALLBACKS_H")
        callbacks_h.append("#define MENU_CALLBACKS_H")
        callbacks_h.append("#include <stdint.h>")
        def gen_callbacks_to(node):
            for c in node.children:
                if c.is_exec:
                    cb = c.callback_name if c.callback_name else f"menu_cb_{c.id}"
                    cb = _sanitize_ident(cb, f"menu_cb_{c.id}")
                    callbacks_h.append(f"void {cb}(void);")
                    callbacks_c.append(f"void {cb}(void){{}}")
                gen_callbacks_to(c)
        gen_callbacks_to(self.menu_root)
        callbacks_h.append("#endif")
        def gen_nodes_to(lines, node):
            for c in node.children:
                if c.children:
                    gen_nodes_to(lines, c)
            arr_name = f"{_sanitize_ident(node.name, f'node_{node.id}')}_{node.id}_children"
            lines.append(f"MenuItem {arr_name}[{len(node.children)}] = {{")
            for c in node.children:
                child_ptr = f"{_sanitize_ident(c.name, f'node_{c.id}')}_{c.id}_children" if c.children else "NULL"
                cb_name = c.callback_name if c.callback_name else (f"menu_cb_{c.id}" if c.is_exec else "")
                cb_ptr = _sanitize_ident(cb_name, f"menu_cb_{c.id}") if c.is_exec else "NULL"
                lines.append(f'  {{"{c.name}", {1 if c.is_exec else 0}, {len(c.children)}, {child_ptr}, {cb_ptr}}},')
            lines.append("};")
            lines.append("")
        gen_nodes_to(menu_c, self.menu_root)
        root_arr_name = f"{_sanitize_ident(self.menu_root.name, f'node_{self.menu_root.id}')}_{self.menu_root.id}_children"
        menu_c.append(f"MenuItem *menu_root = {root_arr_name};")
        menu_c.append("")
        menu_c.append("void draw_menu(u8g2_t *u8g2, MenuItem *root, uint8_t cursor, uint8_t view_start){")
        menu_c.append("  u8g2_ClearBuffer(u8g2);")
        menu_c.append("  u8g2_SetFont(u8g2, u8g2_font_6x10_tf);")
        menu_c.append("  int base_y = 12; int line_h = 12;")
        menu_c.append("  for (uint8_t i = 0; i < root->child_count; ++i) {")
        menu_c.append("    const char *txt = root->children[i].name;")
        menu_c.append("    int y = base_y + i * line_h;")
        if hasattr(self, 'cb_emit_cjk') and self.cb_emit_cjk.isChecked():
            menu_c.append("    draw_text_mixed(u8g2, txt, 2, y);")
        else:
            menu_c.append("    u8g2_DrawStr(u8g2, 2, y, txt);")
        menu_c.append("  }")
        menu_c.append("  u8g2_SendBuffer(u8g2);")
        menu_c.append("}")

        ascii_h = []
        ascii_c = []
        if hasattr(self, 'cb_emit_font') and self.cb_emit_font.isChecked():
            ascii_h.append(f"#ifndef ASCII_FONT_PX_{px}_H")
            ascii_h.append(f"#define ASCII_FONT_PX_{px}_H")
            ascii_h.append("#include <stdint.h>")
            ascii_h.append(f"extern const uint8_t ascii_font_{px}[];")
            ascii_h.append("#endif")
            ascii_c.append(f"#include \"ascii_font.h\"")
            ascii_c.extend(self._emit_ascii_font_array())

        cjk_h = []
        cjk_c = []
        if hasattr(self, 'cb_emit_cjk') and self.cb_emit_cjk.isChecked():
            cjk_h.append(f"#ifndef CJK_FONT_PX_{px}_H")
            cjk_h.append(f"#define CJK_FONT_PX_{px}_H")
            cjk_h.append("#include <stdint.h>")
            cjk_h.append("#include <u8g2.h>")
            cjk_h.append("typedef struct { uint16_t code; uint32_t offset; uint8_t w; uint8_t h; } GlyphEntry;")
            cjk_h.append(f"extern const uint8_t cjk_bitmap_{px}[];")
            cjk_h.append(f"extern const GlyphEntry cjk_table_{px}[];")
            cjk_h.append("int cjk_find_idx(uint16_t code);")
            cjk_h.append("void draw_cjk_char(u8g2_t *u8g2, uint16_t code, int x, int y);")
            cjk_h.append("void draw_text_mixed(u8g2_t *u8g2, const char *utf8, int x, int y);")
            cjk_h.append("#endif")
            cjk_c.append("#include \"cjk_font.h\"")
            cjk_c.extend(self._emit_cjk_font_subset())
            cjk_c.append("")
            cjk_c.append("int cjk_find_idx(uint16_t code){")
            cjk_c.append(f"  int l=0; int r=(int)(sizeof(cjk_table_{px})/sizeof(GlyphEntry))-1;")
            cjk_c.append("  while(l<=r){")
            cjk_c.append("    int m=(l+r)/2;")
            cjk_c.append(f"    if(cjk_table_{px}[m].code==code) return m;")
            cjk_c.append(f"    if(cjk_table_{px}[m].code<code) l=m+1; else r=m-1;")
            cjk_c.append("  }")
            cjk_c.append("  return -1;")
            cjk_c.append("}")
            cjk_c.append("")
            cjk_c.append("void draw_cjk_char(u8g2_t *u8g2, uint16_t code, int x, int y){")
            cjk_c.append("  int idx=cjk_find_idx(code);")
            cjk_c.append("  if(idx<0) return;")
            cjk_c.append(f"  GlyphEntry e=cjk_table_{px}[idx];")
            cjk_c.append(f"  const uint8_t *p=cjk_bitmap_{px};")
            cjk_c.append("  p+=e.offset;")
            cjk_c.append("  uint8_t stride=(e.w+7)/8;")
            cjk_c.append("  for(uint8_t yy=0; yy<e.h; ++yy){")
            cjk_c.append("    const uint8_t *row=p+yy*stride;")
            cjk_c.append("    uint8_t bit=0; uint8_t b=0;")
            cjk_c.append("    for(uint8_t xx=0; xx<e.w; ++xx){")
            cjk_c.append("      if(bit==0){ b=*row++; bit=8; }")
            cjk_c.append("      uint8_t on=(b&0x80)?1:0; b<<=1; bit--;")
            cjk_c.append("      if(on) u8g2_DrawPixel(u8g2, x+xx, y+yy);")
            cjk_c.append("    }")
            cjk_c.append("  }")
            cjk_c.append("}")
            cjk_c.append("")
            cjk_c.append("static uint32_t utf8_next(const char *s, uint32_t *i){")
            cjk_c.append("  uint8_t c=(uint8_t)s[*i];")
            cjk_c.append("  if(c<0x80){ (*i)++; return c; }")
            cjk_c.append("  if((c&0xE0)==0xC0){ uint32_t cp=(c&0x1F)<<6; c=(uint8_t)s[++(*i)]; cp|=(c&0x3F); (*i)++; return cp; }")
            cjk_c.append("  if((c&0xF0)==0xE0){ uint8_t c1=(uint8_t)s[*i+1]; uint8_t c2=(uint8_t)s[*i+2]; uint32_t cp=((uint32_t)(c&0x0F)<<12)|((uint32_t)(c1&0x3F)<<6)|(uint32_t)(c2&0x3F); *i+=3; return cp; }")
            cjk_c.append("  if((c&0xF8)==0xF0){ uint8_t c1=(uint8_t)s[*i+1]; uint8_t c2=(uint8_t)s[*i+2]; uint8_t c3=(uint8_t)s[*i+3]; uint32_t cp=((uint32_t)(c&0x07)<<18)|((uint32_t)(c1&0x3F)<<12)|((uint32_t)(c2&0x3F)<<6)|(uint32_t)(c3&0x3F); *i+=4; return cp; }")
            cjk_c.append("  (*i)++; return 0x3F;")
            cjk_c.append("}")
            cjk_c.append("")
            cjk_c.append("void draw_text_mixed(u8g2_t *u8g2, const char *utf8, int x, int y){")
            cjk_c.append("  uint32_t i=0; int cx=x;")
            cjk_c.append("  while(utf8[i]){")
            cjk_c.append("    uint32_t cp=utf8_next(utf8,&i);")
            cjk_c.append("    if(cp<128){ char buf[2]; buf[0]=(char)cp; buf[1]='\0'; u8g2_DrawStr(u8g2, cx, y, buf); cx += u8g2_GetStrWidth(u8g2, buf); }")
            cjk_c.append(f"    else {{ int idx=cjk_find_idx((uint16_t)cp); if(idx>=0){{ GlyphEntry e=cjk_table_{px}[idx]; draw_cjk_char(u8g2,(uint16_t)cp,cx,y - e.h + u8g2_GetMaxCharHeight(u8g2)); cx += e.w + 1; }} else {{ u8g2_DrawStr(u8g2, cx, y, \"?\"); cx += u8g2_GetStrWidth(u8g2, \"?\"); }} }}")
            cjk_c.append("  }")
            cjk_c.append("}")

        def _write(path, lines):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        mui_dir = os.path.join(out_dir, "MUI")
        no_u8g2 = hasattr(self, 'cb_no_u8g2') and self.cb_no_u8g2.isChecked()
        if not no_u8g2:
            menu_dir = os.path.join(mui_dir, "menu")
            fonts_dir = os.path.join(mui_dir, "fonts")
            callbacks_dir = os.path.join(mui_dir, "callbacks")
            _write(os.path.join(menu_dir, "menu.h"), menu_h)
            _write(os.path.join(menu_dir, "menu.c"), menu_c)
            if ascii_h:
                _write(os.path.join(fonts_dir, "ascii_font.h"), ascii_h)
                _write(os.path.join(fonts_dir, "ascii_font.c"), ascii_c)
            if cjk_h:
                _write(os.path.join(fonts_dir, "cjk_font.h"), cjk_h)
                _write(os.path.join(fonts_dir, "cjk_font.c"), cjk_c)
            _write(os.path.join(callbacks_dir, "callbacks.h"), callbacks_h)
            _write(os.path.join(callbacks_dir, "callbacks.c"), callbacks_c)
            # 导出移植接口与聚合头
            port_h = []
            port_h.append("#ifndef PORTING_INTERFACE_H")
            port_h.append("#define PORTING_INTERFACE_H")
            port_h.append("#include <stdint.h>")
            port_h.append("#include \"menu/menu.h\"")
            port_h.append("typedef enum { MENU_KEY_NONE=0, MENU_KEY_UP, MENU_KEY_DOWN, MENU_KEY_ENTER, MENU_KEY_BACK } MenuKey;")
            port_h.append("typedef struct { uint8_t cursor; uint8_t view_start; } MenuState;")
            port_h.append("typedef struct { MenuItem* current; MenuItem* stack[16]; uint8_t depth; MenuState state; } MenuNav;")
            port_h.append("void menu_nav_init(MenuNav* nav, MenuItem* root);")
            port_h.append("void menu_nav_on_key(MenuNav* nav, MenuKey key, uint8_t visible_lines);")
            port_h.append("#endif")
            _write(os.path.join(mui_dir, "porting_interface.h"), port_h)

            port_c = []
            port_c.append("#include \"porting_interface.h\"")
            port_c.append("")
            port_c.append("void menu_nav_init(MenuNav* nav, MenuItem* root){")
            port_c.append("  nav->current = root;")
            port_c.append("  nav->depth = 0;")
            port_c.append("  nav->state.cursor = 0;")
            port_c.append("  nav->state.view_start = 0;")
            port_c.append("}")
            port_c.append("")
            port_c.append("void menu_nav_on_key(MenuNav* nav, MenuKey key, uint8_t visible_lines){")
            port_c.append("  if(!nav || !nav->current) return;")
            port_c.append("  uint8_t count = nav->current->child_count;")
            port_c.append("  switch(key){")
            port_c.append("    case MENU_KEY_UP: if(nav->state.cursor > 0) nav->state.cursor--; break;")
            port_c.append("    case MENU_KEY_DOWN: if(nav->state.cursor + 1 < count) nav->state.cursor++; break;")
            port_c.append("    case MENU_KEY_ENTER: {")
            port_c.append("      MenuItem* sel = &nav->current->children[nav->state.cursor];")
            port_c.append("      if(sel->is_exec && sel->callback) sel->callback();")
            port_c.append("      else if(sel->child_count){ if(nav->depth < 16) nav->stack[nav->depth++] = nav->current; nav->current = sel; nav->state.cursor = 0; nav->state.view_start = 0; }")
            port_c.append("    } break;")
            port_c.append("    case MENU_KEY_BACK: if(nav->depth > 0){ nav->current = nav->stack[--nav->depth]; nav->state.cursor = 0; nav->state.view_start = 0; } break;")
            port_c.append("    default: break;")
            port_c.append("  }")
            port_c.append("  if(nav->state.cursor < nav->state.view_start) nav->state.view_start = nav->state.cursor;")
            port_c.append("  if(visible_lines > 0 && nav->state.cursor >= nav->state.view_start + visible_lines) nav->state.view_start = nav->state.cursor - visible_lines + 1;")
            port_c.append("}")
            _write(os.path.join(mui_dir, "porting_interface.c"), port_c)
            bundle_h = []
            bundle_h.append("#ifndef U8G2_CODE_BUNDLE_H")
            bundle_h.append("#define U8G2_CODE_BUNDLE_H")
            bundle_h.append("#include \"menu/menu.h\"")
            bundle_h.append("#include \"porting_interface.h\"")
            bundle_h.append("#include \"callbacks/callbacks.h\"")
            if cjk_h:
                bundle_h.append("#include \"fonts/cjk_font.h\"")
            bundle_h.append("#endif")
            _write(os.path.join(mui_dir, "mui_bundle.h"), bundle_h)
        else:
            bare_dir = mui_dir
            bare_menu_h = []
            bare_menu_h.append("#ifndef MENU_BARE_H")
            bare_menu_h.append("#define MENU_BARE_H")
            bare_menu_h.append("#include <stdint.h>")
            bare_menu_h.append("typedef struct MenuItem { const char *name; uint8_t is_exec; uint8_t child_count; struct MenuItem *children; void (*callback)(void); } MenuItem;")
            bare_menu_h.append("extern MenuItem *menu_root;")
            bare_menu_h.append("void draw_menu_bare(uint8_t cursor, uint8_t view_start);")
            bare_menu_h.append("#endif")
            bare_menu_c = []
            bare_menu_c.append("#include \"menu_bare.h\"")
            bare_menu_c.append("#include \"gfx_port.h\"")
            def gen_callbacks_to_bare(lines, node):
                for c in node.children:
                    if c.is_exec:
                        cb = c.callback_name if c.callback_name else f"menu_cb_{c.id}"
                        cb = _sanitize_ident(cb, f"menu_cb_{c.id}")
                        lines.append(f"void {cb}(void){{}}")
                    gen_callbacks_to_bare(lines, c)
            gen_callbacks_to_bare(bare_menu_c, self.menu_root)
            bare_menu_c.append("")
            def gen_nodes_bare(lines, node):
                for c in node.children:
                    if c.children:
                        gen_nodes_bare(lines, c)
                arr_name = f"{_sanitize_ident(node.name, f'node_{node.id}')}_{node.id}_children"
                lines.append(f"MenuItem {arr_name}[{len(node.children)}] = {{")
                for c in node.children:
                    child_ptr = f"{_sanitize_ident(c.name, f'node_{c.id}')}_{c.id}_children" if c.children else "NULL"
                    cb_name = c.callback_name if c.callback_name else (f"menu_cb_{c.id}" if c.is_exec else "")
                    cb_ptr = _sanitize_ident(cb_name, f"menu_cb_{c.id}") if c.is_exec else "NULL"
                    lines.append(f'  {{"{c.name}", {1 if c.is_exec else 0}, {len(c.children)}, {child_ptr}, {cb_ptr}}},')
                lines.append("};")
                lines.append("")
            gen_nodes_bare(bare_menu_c, self.menu_root)
            root_arr_name_bare = f"{_sanitize_ident(self.menu_root.name, f'node_{self.menu_root.id}')}_{self.menu_root.id}_children"
            bare_menu_c.append(f"MenuItem *menu_root = {root_arr_name_bare};")
            bare_menu_c.append("")
            bare_menu_c.append("void draw_menu_bare(uint8_t cursor, uint8_t view_start){")
            bare_menu_c.append("  int base_y=12; int line_h=12;")
            bare_menu_c.append("  gfx_clear();")
            bare_menu_c.append("  for(uint8_t i=0;i<menu_root->child_count;i++){ const char* txt=menu_root->children[i].name; int y=base_y + i*line_h; gfx_draw_text_mixed(2,y,txt);")
            bare_menu_c.append("  }")
            bare_menu_c.append("  gfx_send();")
            bare_menu_c.append("}")
            gfx_h = []
            gfx_h.append("#ifndef GFX_PORT_H")
            gfx_h.append("#define GFX_PORT_H")
            gfx_h.append("#include <stdint.h>")
            gfx_h.append("void gfx_init(void);")
            gfx_h.append("void gfx_clear(void);")
            gfx_h.append("void gfx_send(void);")
            gfx_h.append("void gfx_draw_pixel(int x,int y);")
            gfx_h.append("void gfx_fill_rect(int x,int y,int w,int h);")
            gfx_h.append("void gfx_draw_bitmap_1bpp(int x,int y,int w,int h,const uint8_t* data);")
            gfx_h.append("void gfx_draw_text_mixed(int x,int y,const char* utf8);")
            gfx_h.append("#endif")
            gfx_c = []
            gfx_c.append("#include \"gfx_port.h\"")
            if hasattr(self, 'cb_emit_font') and self.cb_emit_font.isChecked():
                gfx_c.extend(self._emit_ascii_font_full())
            if hasattr(self, 'cb_emit_cjk') and self.cb_emit_cjk.isChecked():
                gfx_c.extend(self._emit_cjk_font_subset())
            gfx_c.append("")
            gfx_c.append("void gfx_init(void){}");
            gfx_c.append("void gfx_clear(void){}");
            gfx_c.append("void gfx_send(void){}");
            gfx_c.append("void gfx_draw_pixel(int x,int y){}");
            gfx_c.append("void gfx_fill_rect(int x,int y,int w,int h){ for(int yy=0; yy<h; ++yy){ for(int xx=0; xx<w; ++xx){ gfx_draw_pixel(x+xx,y+yy); } } }");
            gfx_c.append("void gfx_draw_bitmap_1bpp(int x,int y,int w,int h,const uint8_t* data){ int stride=(w+7)/8; for(int yy=0; yy<h; ++yy){ const uint8_t* row=data+yy*stride; int bit=0; uint8_t b=0; for(int xx=0; xx<w; ++xx){ if(bit==0){ b=*row++; bit=8; } int on=(b&0x80)?1:0; b<<=1; bit--; if(on) gfx_draw_pixel(x+xx,y+yy); } } }");
            gfx_c.append("static int find_ascii(uint16_t code){ extern const AsciiGlyph ascii_table_" + str(px) + "[]; int n=sizeof(ascii_table_" + str(px) + ")/sizeof(AsciiGlyph); int l=0,r=n-1; while(l<=r){ int m=(l+r)/2; if(ascii_table_" + str(px) + "[m].code==code) return m; if(ascii_table_" + str(px) + "[m].code<code) l=m+1; else r=m-1;} return -1; }")
            gfx_c.append("void gfx_draw_text_mixed(int x,int y,const char* utf8){")
            gfx_c.append("  uint32_t i=0; int cx=x; while(utf8[i]){ uint8_t c=(uint8_t)utf8[i]; if(c<128){ int idx=find_ascii(c); if(idx>=0){ extern const uint8_t ascii_bitmap_" + str(px) + "[]; extern const AsciiGlyph ascii_table_" + str(px) + "[]; const AsciiGlyph a=ascii_table_" + str(px) + "[idx]; gfx_draw_bitmap_1bpp(cx, y-a.h+12, a.w, a.h, ascii_bitmap_" + str(px) + "+ a.offset); cx += a.w + 1; } i++; } else {")
            gfx_c.append("    uint8_t c1=(uint8_t)utf8[i+1]; uint8_t c2=(uint8_t)utf8[i+2]; uint16_t cp=((c & 0x0F)<<12) | ((c1 & 0x3F)<<6) | (c2 & 0x3F); i+=3; ")
            gfx_c.append("    int idx=cjk_find_idx(cp); if(idx>=0){ extern const uint8_t cjk_bitmap_" + str(px) + "[]; extern const GlyphEntry cjk_table_" + str(px) + "[]; GlyphEntry e=cjk_table_" + str(px) + "[idx]; gfx_draw_bitmap_1bpp(cx, y-e.h+12, e.w, e.h, cjk_bitmap_" + str(px) + "+ e.offset); cx += e.w + 1; } else { cx += 6; } }")
            gfx_c.append("  }")
            gfx_c.append("}")
            example_c = []
            example_c.append("#include \"menu_bare.h\"")
            example_c.append("#include \"gfx_port.h\"")
            example_c.append("#include \"input_port.h\"")
            example_c.append("#include <stdint.h>")
            example_c.append("int main(void){ gfx_init(); uint8_t cursor=0, view_start=0; for(;;){ MenuKey k=input_port_read(); (void)k; gfx_clear(); draw_menu_bare(cursor,view_start); gfx_send(); } return 0; }")
            os.makedirs(os.path.join(bare_dir, "menu"), exist_ok=True)
            os.makedirs(os.path.join(bare_dir, "port"), exist_ok=True)
            os.makedirs(os.path.join(bare_dir, "examples"), exist_ok=True)
            _write(os.path.join(bare_dir, "menu", "menu_bare.h"), bare_menu_h)
            _write(os.path.join(bare_dir, "menu", "menu_bare.c"), bare_menu_c)
            _write(os.path.join(bare_dir, "port", "gfx_port.h"), gfx_h)
            _write(os.path.join(bare_dir, "port", "gfx_port.c"), gfx_c)
            # 输入接口文件
            input_h = []
            input_h.append("#ifndef INPUT_PORT_H")
            input_h.append("#define INPUT_PORT_H")
            input_h.append("#include <stdint.h>")
            input_h.append("typedef enum { MENU_KEY_NONE=0, MENU_KEY_UP, MENU_KEY_DOWN, MENU_KEY_ENTER, MENU_KEY_BACK } MenuKey;")
            input_h.append("MenuKey input_port_read(void);")
            input_h.append("#endif")
            input_c = []
            input_c.append("#include \"input_port.h\"")
            input_c.append("MenuKey input_port_read(void){ return MENU_KEY_NONE; }")
            _write(os.path.join(bare_dir, "port", "input_port.h"), input_h)
            _write(os.path.join(bare_dir, "port", "input_port.c"), input_c)
            _write(os.path.join(bare_dir, "examples", "example_bare.c"), example_c)
            # STM32 StdPeriph implementation templates
            stm_dir = os.path.join(bare_dir, "port", "stm32_std")
            os.makedirs(stm_dir, exist_ok=True)
            stm_gfx = []
            stm_gfx.append("#include \"stm32f10x.h\"")
            stm_gfx.append("#include \"stm32f10x_rcc.h\"")
            stm_gfx.append("#include \"stm32f10x_gpio.h\"")
            stm_gfx.append("#include \"stm32f10x_i2c.h\"")
            stm_gfx.append("#include \"gfx_port.h\"")
            stm_gfx.append("#define SSD1306_ADDR 0x3C")
            stm_gfx.append("#define GFX_W 128")
            stm_gfx.append("#define GFX_H 64")
            stm_gfx.append("static uint8_t fb[GFX_W*GFX_H/8];")
            stm_gfx.append("static void clock_init(void){ RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB|RCC_APB2Periph_GPIOA, ENABLE); RCC_APB1PeriphClockCmd(RCC_APB1Periph_I2C1, ENABLE); }")
            stm_gfx.append("static void gpio_init(void){ GPIO_InitTypeDef gi; gi.GPIO_Pin=GPIO_Pin_6|GPIO_Pin_7; gi.GPIO_Speed=GPIO_Speed_50MHz; gi.GPIO_Mode=GPIO_Mode_AF_OD; GPIO_Init(GPIOB,&gi); gi.GPIO_Pin=GPIO_Pin_0|GPIO_Pin_1|GPIO_Pin_2|GPIO_Pin_3; gi.GPIO_Speed=GPIO_Speed_50MHz; gi.GPIO_Mode=GPIO_Mode_IPU; GPIO_Init(GPIOA,&gi); }")
            stm_gfx.append("static void i2c1_init(void){ I2C_InitTypeDef ii; I2C_DeInit(I2C1); ii.I2C_ClockSpeed=400000; ii.I2C_Mode=I2C_Mode_I2C; ii.I2C_DutyCycle=I2C_DutyCycle_2; ii.I2C_OwnAddress1=0x00; ii.I2C_Ack=I2C_Ack_Disable; ii.I2C_AcknowledgedAddress=I2C_AcknowledgedAddress_7bit; I2C_Init(I2C1,&ii); I2C_Cmd(I2C1,ENABLE); }")
            stm_gfx.append("static void i2c1_write(uint8_t control,const uint8_t* data,int len){ while(I2C_GetFlagStatus(I2C1,I2C_FLAG_BUSY)); I2C_GenerateSTART(I2C1,ENABLE); while(!I2C_CheckEvent(I2C1,I2C_EVENT_MASTER_MODE_SELECT)); I2C_Send7bitAddress(I2C1,SSD1306_ADDR<<1,I2C_Direction_Transmitter); while(!I2C_CheckEvent(I2C1,I2C_EVENT_MASTER_TRANSMITTER_MODE_SELECTED)); I2C_SendData(I2C1,control); while(!I2C_CheckEvent(I2C1,I2C_EVENT_MASTER_BYTE_TRANSMITTED)); for(int i=0;i<len;i++){ I2C_SendData(I2C1,data[i]); while(!I2C_CheckEvent(I2C1,I2C_EVENT_MASTER_BYTE_TRANSMITTED)); } I2C_GenerateSTOP(I2C1,ENABLE); }")
            stm_gfx.append("static void ssd1306_cmd(uint8_t c){ i2c1_write(0x00,&c,1); }")
            stm_gfx.append("static void ssd1306_data(const uint8_t* d,int n){ i2c1_write(0x40,d,n); }")
            stm_gfx.append("void gfx_init(void){ clock_init(); gpio_init(); i2c1_init(); ssd1306_cmd(0xAE); ssd1306_cmd(0x20); ssd1306_cmd(0x00); ssd1306_cmd(0xB0); ssd1306_cmd(0xC8); ssd1306_cmd(0x00); ssd1306_cmd(0x10); ssd1306_cmd(0x40); ssd1306_cmd(0x81); ssd1306_cmd(0x7F); ssd1306_cmd(0xA1); ssd1306_cmd(0xA6); ssd1306_cmd(0xA8); ssd1306_cmd(0x3F); ssd1306_cmd(0xA4); ssd1306_cmd(0xD3); ssd1306_cmd(0x00); ssd1306_cmd(0xD5); ssd1306_cmd(0x80); ssd1306_cmd(0xD9); ssd1306_cmd(0xF1); ssd1306_cmd(0xDA); ssd1306_cmd(0x12); ssd1306_cmd(0xDB); ssd1306_cmd(0x40); ssd1306_cmd(0x8D); ssd1306_cmd(0x14); ssd1306_cmd(0xAF); }")
            stm_gfx.append("void gfx_clear(void){ for(int i=0;i<sizeof(fb);i++) fb[i]=0x00; }")
            stm_gfx.append("void gfx_send(void){ for(uint8_t page=0; page<(GFX_H/8); page++){ ssd1306_cmd(0xB0+page); ssd1306_cmd(0x00); ssd1306_cmd(0x10); ssd1306_data(&fb[page*GFX_W], GFX_W); } }")
            stm_gfx.append("void gfx_draw_pixel(int x,int y){ if(x<0||x>=GFX_W||y<0||y>=GFX_H) return; fb[(y>>3)*GFX_W + x] |= (1<<(y&7)); }")
            stm_gfx.append("void gfx_fill_rect(int x,int y,int w,int h){ for(int yy=0; yy<h; ++yy){ for(int xx=0; xx<w; ++xx){ gfx_draw_pixel(x+xx,y+yy); } } }")
            stm_gfx.append("void gfx_draw_bitmap_1bpp(int x,int y,int w,int h,const uint8_t* data){ int stride=(w+7)/8; for(int yy=0; yy<h; ++yy){ const uint8_t* row=data+yy*stride; int bit=0; uint8_t b=0; for(int xx=0; xx<w; ++xx){ if(bit==0){ b=*row++; bit=8; } if(b&0x80) gfx_draw_pixel(x+xx,y+yy); b<<=1; bit--; } } }")
            _write(os.path.join(stm_dir, "gfx_port_stm32_std.c"), stm_gfx)
            stm_input = []
            stm_input.append("#include \"stm32f10x.h\"")
            stm_input.append("#include \"stm32f10x_rcc.h\"")
            stm_input.append("#include \"stm32f10x_gpio.h\"")
            stm_input.append("#include \"input_port.h\"")
            stm_input.append("static void input_init(void){ RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE); GPIO_InitTypeDef gi; gi.GPIO_Pin=GPIO_Pin_0|GPIO_Pin_1|GPIO_Pin_2|GPIO_Pin_3; gi.GPIO_Speed=GPIO_Speed_50MHz; gi.GPIO_Mode=GPIO_Mode_IPU; GPIO_Init(GPIOA,&gi); }")
            stm_input.append("MenuKey input_port_read(void){ static int inited=0; if(!inited){ input_init(); inited=1; } if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_0)==Bit_RESET) return MENU_KEY_UP; if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_1)==Bit_RESET) return MENU_KEY_DOWN; if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_2)==Bit_RESET) return MENU_KEY_ENTER; if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_3)==Bit_RESET) return MENU_KEY_BACK; return MENU_KEY_NONE; }")
            _write(os.path.join(stm_dir, "input_port_stm32_std.c"), stm_input)
        print(f"MUI 代码已导出到目录: {mui_dir}")

# ---------------- Main ----------------
if __name__=="__main__":
    app = QApplication([])
    w = MenuDesigner()
    w.show()
    app.exec()
