# mcu_menu_designer_u8g2_final_complete.py
from PySide6.QtWidgets import (QApplication, QWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QGroupBox, QComboBox)
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont
from PySide6.QtCore import Qt

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
        
        # 设置默认颜色
        self.bg_color = Qt.black
        self.fg_color = QColor(0, 255, 0)  # OLED绿色
        self.selected_bg_color = QColor(0, 255, 0)
        self.selected_fg_color = Qt.black
        
        # 创建framebuffer，使用更高质量的图像格式
        self.framebuffer = QPixmap(self.fb_w, self.fb_h)
        self.framebuffer.fill(self.bg_color)
        
        # 设置framebuffer属性以提高文本渲染质量
        self.framebuffer.setDevicePixelRatio(1.0)
        
        self.update_preview_size()
        self.menu_root = None
        self.cursor_index = 0
        self.current_page = 0
        
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

    def set_screen_type(self, screen_type, color_mode="单色", font_size="小(8px)", 
                        font_color="白色", bg_color="深蓝色", selected_bg="白色", selected_font="黑色"):
        """设置屏幕类型和相关参数"""
        self.screen_type = screen_type
        self.color_mode = color_mode
        
        # 根据屏幕类型调整参数
        if screen_type == "128x128 OLED":
            self.fb_w, self.fb_h = 128, 128
            self.base_font_px = 8
            self.max_lines = 16
            self.bg_color = Qt.black
            self.fg_color = QColor(0, 255, 0)  # OLED绿色
            self.selected_bg_color = QColor(0, 255, 0)
            self.selected_fg_color = Qt.black
        elif screen_type == "128x128 TFT":
            self.fb_w, self.fb_h = 128, 128
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
            self.fb_w, self.fb_h = 128, 128
            self.base_font_px = 8
            self.max_lines = 16
            self.bg_color = Qt.black
            self.fg_color = QColor(0, 255, 0)  # OLED绿色
            self.selected_bg_color = QColor(0, 255, 0)
            self.selected_fg_color = Qt.black
        
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
        
        # 计算显示起始位置
        if max_lines >= total:
            start = 0
            self.show_scrollbar = False
        else:
            self.show_scrollbar = True
            # 更智能的滚动逻辑：光标位于合理位置
            if self.cursor_index < max_lines // 2:
                start = 0
            elif self.cursor_index >= total - max_lines // 2:
                start = max(0, total - max_lines)
            else:
                start = self.cursor_index - max_lines // 2
            
            # 计算当前页码
            self.current_page = start // max_lines
        
 # 固定底部导航高度，始终显示底部导航组件
        bottom_nav_height = self.base_font_px + 6  # 底部导航区域高度
        
        # 调整最大行数以适应底部导航
        effective_height = self.fb_h - bottom_nav_height
        max_lines = effective_height // (self.base_font_px + 2)  # 重新计算最大行数
        max_lines = max(max_lines, 1)  # 确保至少显示一行
        
        # 重新计算显示起始位置
        if max_lines >= total:
            start = 0
            self.show_scrollbar = False
        else:
            self.show_scrollbar = True
            # 更智能的滚动逻辑：光标位于合理位置
            if self.cursor_index < max_lines // 2:
                start = 0
            elif self.cursor_index >= total - max_lines // 2:
                start = max(0, total - max_lines)
            else:
                start = self.cursor_index - max_lines // 2
            
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
                    painter.drawPoint(x, i * line_h + line_h // 2)
                break
                
            item = visible[idx]
            y = i * line_h + line_h
            
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
                # 绘制完整的选中背景，保持原来的样子
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

    def _get_font(self):
        """获取合适的字体"""
        from PySide6.QtGui import QFont
        # 使用更适合像素级显示的字体
        if "OLED" in self.screen_type:
            # OLED屏幕使用更适合低分辨率显示的字体
            font = QFont("Courier New", max(self.base_font_px, 8))  # 使用等宽字体，最小8px
            font.setStyleStrategy(QFont.NoAntialias)  # 禁用抗锯齿，保持像素级清晰
            font.setHintingPreference(QFont.PreferFullHinting)  # 使用完整字体提示
        else:
            font = QFont("Microsoft YaHei", max(self.base_font_px, 10))  # 其他屏幕使用微软雅黑
            font.setStyleStrategy(QFont.PreferAntialias)  # 其他屏幕可以使用抗锯齿
            
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
        self.resize(1200,700)
        
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
            'selected_font': '#000000'
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
        left_widget.setMaximumWidth(250)  # 限制左侧宽度
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)  # 增加内部间距
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("菜单结构")
        self.tree.itemClicked.connect(self.on_tree_select)
        self.tree.setMinimumHeight(400)  # 设置最小高度
        self.refresh_tree()
        left_layout.addWidget(self.tree)
        left_layout.addStretch()
        
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
        
        # 创建预览控件
        self.preview = MenuPreview()
        self.preview.setMinimumHeight(300)  # 增加预览最小高度
        preview_layout.addWidget(self.preview, 1)
        
        middle_layout.addWidget(preview_group)
        
        # 按键模拟
        keys_group = QGroupBox("按键模拟")
        keys_layout = QVBoxLayout(keys_group)
        keys_layout.setSpacing(8)
        keys_layout.setContentsMargins(12, 12, 12, 12)
        
        # 嵌入式风格四键布局 - 上方一个，下方三个
        keys_grid_layout = QVBoxLayout()
        keys_grid_layout.setSpacing(10)
        keys_grid_layout.setContentsMargins(5, 5, 5, 5)
        
        # 上方一个按键（居中）
        top_row = QHBoxLayout()
        top_row.setSpacing(0)
        top_row.addStretch()
        self.key_up_btn = QPushButton("↑")
        self.key_up_btn.setProperty("class", "key-btn")
        self.key_up_btn.setFixedSize(50, 40)  # 稍大一些，作为主按键
        self.key_up_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 5px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        top_row.addWidget(self.key_up_btn)
        top_row.addStretch()
        
        # 下方三个按键（水平排列）
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        bottom_row.addStretch()
        
        # 左键
        self.key_left_btn = QPushButton("←")
        self.key_left_btn.setProperty("class", "key-btn")
        self.key_left_btn.setFixedSize(45, 35)  # 适中大小
        self.key_left_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_left_btn)
        
        # 下键
        self.key_down_btn = QPushButton("↓")
        self.key_down_btn.setProperty("class", "key-btn")
        self.key_down_btn.setFixedSize(45, 35)  # 与左键相同
        self.key_down_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_down_btn)
        
        # 右键
        self.key_right_btn = QPushButton("→")
        self.key_right_btn.setProperty("class", "key-btn")
        self.key_right_btn.setFixedSize(45, 35)  # 与其他键相同
        self.key_right_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_right_btn)
        
        bottom_row.addStretch()
        
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
        
        # 连接按键事件（修改为支持四个方向键）
        self.key_up_btn.clicked.connect(lambda: self.on_key("Up"))
        self.key_down_btn.clicked.connect(lambda: self.on_key("Down"))
        self.key_left_btn.clicked.connect(lambda: self.on_key("Left"))
        self.key_right_btn.clicked.connect(lambda: self.on_key("Right"))
        
        # 添加确认和返回功能到方向键
        # 这里我们暂时不创建确认和返回按钮，而是用方向键的组合来实现
        # 可以考虑长按或者双击等操作，但目前先保持四个方向键
        
        # middle_layout.addWidget(keys_group)  # 从中间布局移除按键组
        
        main_layout.addWidget(middle_widget, 1)  # 中间自适应宽度

        # === 右侧：配置与操作 ===
        right_widget = QWidget()
        right_widget.setMaximumWidth(320)  # 限制右侧宽度
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 首先添加按键模拟组到右下角
        keys_group = QGroupBox("按键模拟")
        keys_layout = QVBoxLayout(keys_group)
        keys_layout.setSpacing(8)
        keys_layout.setContentsMargins(12, 12, 12, 12)
        
        # 嵌入式风格四键布局 - 上方一个，下方三个
        keys_grid_layout = QVBoxLayout()
        keys_grid_layout.setSpacing(10)
        keys_grid_layout.setContentsMargins(5, 5, 5, 5)
        
        # 上方一个按键（居中）
        top_row = QHBoxLayout()
        top_row.setSpacing(0)
        top_row.addStretch()
        self.key_up_btn = QPushButton("↑")
        self.key_up_btn.setProperty("class", "key-btn")
        self.key_up_btn.setFixedSize(50, 40)  # 稍大一些，作为主按键
        self.key_up_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 5px;
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        top_row.addWidget(self.key_up_btn)
        top_row.addStretch()
        
        # 下方三个按键（水平排列）
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        bottom_row.addStretch()
        
        # 左键
        self.key_left_btn = QPushButton("←")
        self.key_left_btn.setProperty("class", "key-btn")
        self.key_left_btn.setFixedSize(45, 35)  # 适中大小
        self.key_left_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_left_btn)
        
        # 下键
        self.key_down_btn = QPushButton("↓")
        self.key_down_btn.setProperty("class", "key-btn")
        self.key_down_btn.setFixedSize(45, 35)  # 与左键相同
        self.key_down_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_down_btn)
        
        # 右键
        self.key_right_btn = QPushButton("→")
        self.key_right_btn.setProperty("class", "key-btn")
        self.key_right_btn.setFixedSize(45, 35)  # 与其他键相同
        self.key_right_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5a, stop:1 #3a3a3a);
                border: 2px solid #2a2a2a;
                border-radius: 4px;
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6a6a6a, stop:1 #4a4a4a);
                border-color: #0078d4;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1a1a1a);
                border-color: #005a9e;
            }
        """)
        bottom_row.addWidget(self.key_right_btn)
        
        bottom_row.addStretch()
        
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
        self.export_btn = QPushButton("导出U8G2 C代码")
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
        
        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        
        # 屏幕类型选择
        screen_type_layout = QHBoxLayout()
        screen_type_layout.addWidget(QLabel("屏幕类型:"))
        self.screen_type_combo = QComboBox()
        self.screen_type_combo.addItems(["128x128 OLED", "128x128 TFT"])
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
        
        # 颜色模式选择
        color_mode_layout = QHBoxLayout()
        color_mode_layout.addWidget(QLabel("颜色模式:"))
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(["单色", "16色", "256色", "真彩色"])
        self.color_mode_combo.currentTextChanged.connect(self.on_screen_config_changed)
        color_mode_layout.addWidget(self.color_mode_combo)
        color_mode_layout.addStretch()
        
        # 字体大小选择
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["小(8px)", "中(12px)", "大(16px)"])
        self.font_size_combo.setCurrentText("中(12px)")
        self.font_size_combo.currentTextChanged.connect(self.on_screen_config_changed)
        font_size_layout.addWidget(self.font_size_combo)
        font_size_layout.addStretch()
        
        # 预览窗口大小设置
        preview_size_layout = QHBoxLayout()
        preview_size_layout.addWidget(QLabel("预览缩放:"))
        self.preview_size_combo = QComboBox()
        self.preview_size_combo.addItems(["实际大小", "放大1.5倍", "放大2倍", "放大3倍"])
        self.preview_size_combo.setCurrentText("实际大小")
        self.preview_size_combo.currentTextChanged.connect(self.on_preview_size_changed)
        preview_size_layout.addWidget(self.preview_size_combo)
        preview_size_layout.addStretch()
        
        display_layout.addLayout(color_mode_layout)
        display_layout.addLayout(font_size_layout)
        display_layout.addLayout(preview_size_layout)
        
        # 颜色配置组（仅TFT模式）
        color_group = QGroupBox("颜色配置 (TFT模式)")
        color_layout = QVBoxLayout(color_group)
        color_layout.setSpacing(8)
        color_layout.setContentsMargins(10, 10, 10, 10)
        
        # 背景颜色选择
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("背景颜色:"))
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setText("选择颜色")
        self.bg_color_btn.setStyleSheet("background-color: rgb(0, 64, 128); color: white;")
        self.bg_color_btn.setProperty("class", "color-btn")
        self.bg_color_btn.clicked.connect(lambda: self.choose_color('bg'))
        self.bg_color_btn.setMaximumWidth(80)
        bg_color_layout.addWidget(self.bg_color_btn)
        
        self.bg_color_hex = QLineEdit("#004080")
        self.bg_color_hex.setMaximumWidth(60)
        self.bg_color_hex.textChanged.connect(self.on_hex_color_changed)
        bg_color_layout.addWidget(QLabel("HEX:"))
        bg_color_layout.addWidget(self.bg_color_hex)
        bg_color_layout.addStretch()
        
        # 字体颜色选择
        font_color_layout = QHBoxLayout()
        font_color_layout.addWidget(QLabel("字体颜色:"))
        self.font_color_btn = QPushButton()
        self.font_color_btn.setText("选择颜色")
        self.font_color_btn.setStyleSheet("background-color: rgb(255, 255, 255); color: black;")
        self.font_color_btn.setProperty("class", "color-btn")
        self.font_color_btn.clicked.connect(lambda: self.choose_color('font'))
        self.font_color_btn.setMaximumWidth(80)
        font_color_layout.addWidget(self.font_color_btn)
        
        self.font_color_hex = QLineEdit("#FFFFFF")
        self.font_color_hex.setMaximumWidth(60)
        self.font_color_hex.textChanged.connect(self.on_hex_color_changed)
        font_color_layout.addWidget(QLabel("HEX:"))
        font_color_layout.addWidget(self.font_color_hex)
        font_color_layout.addStretch()
        
        # 选中项背景颜色
        selected_bg_layout = QHBoxLayout()
        selected_bg_layout.addWidget(QLabel("选中背景:"))
        self.selected_bg_btn = QPushButton()
        self.selected_bg_btn.setText("选择颜色")
        self.selected_bg_btn.setStyleSheet("background-color: rgb(255, 255, 255); color: black;")
        self.selected_bg_btn.setProperty("class", "color-btn")
        self.selected_bg_btn.clicked.connect(lambda: self.choose_color('selected_bg'))
        self.selected_bg_btn.setMaximumWidth(80)
        selected_bg_layout.addWidget(self.selected_bg_btn)
        
        self.selected_bg_hex = QLineEdit("#FFFFFF")
        self.selected_bg_hex.setMaximumWidth(60)
        self.selected_bg_hex.textChanged.connect(self.on_hex_color_changed)
        selected_bg_layout.addWidget(QLabel("HEX:"))
        selected_bg_layout.addWidget(self.selected_bg_hex)
        selected_bg_layout.addStretch()
        
        # 选中项字体颜色
        selected_font_layout = QHBoxLayout()
        selected_font_layout.addWidget(QLabel("选中字体:"))
        self.selected_font_btn = QPushButton()
        self.selected_font_btn.setText("选择颜色")
        self.selected_font_btn.setStyleSheet("background-color: rgb(0, 0, 0); color: white;")
        self.selected_font_btn.setProperty("class", "color-btn")
        self.selected_font_btn.clicked.connect(lambda: self.choose_color('selected_font'))
        self.selected_font_btn.setMaximumWidth(80)
        selected_font_layout.addWidget(self.selected_font_btn)
        
        self.selected_font_hex = QLineEdit("#000000")
        self.selected_font_hex.setMaximumWidth(60)
        self.selected_font_hex.textChanged.connect(self.on_hex_color_changed)
        selected_font_layout.addWidget(QLabel("HEX:"))
        selected_font_layout.addWidget(self.selected_font_hex)
        selected_font_layout.addStretch()
        
        color_layout.addLayout(bg_color_layout)
        color_layout.addLayout(font_color_layout)
        color_layout.addLayout(selected_bg_layout)
        color_layout.addLayout(selected_font_layout)
        
        # 添加到配置选项卡
        config_tab_layout.addWidget(basic_group)
        config_tab_layout.addWidget(display_group)
        config_tab_layout.addWidget(color_group)
        config_tab_layout.addStretch()
        
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
            self.color_mode_combo.currentText(),
            self.font_size_combo.currentText()
        )
        self.preview.menu_root = self.menu_root
        self.preview.render_menu()
        
        # 连接选项卡切换信号，用于动态显示/隐藏颜色配置
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 初始状态：如果不是TFT模式，隐藏颜色配置
        if "OLED" in self.screen_type_combo.currentText():
            self.toggle_color_config(False)

    # ---------------- 配置处理方法 ----------------
    def on_screen_type_changed(self):
        """屏幕类型改变时更新配置，保存当前设置"""
        screen_type = self.screen_type_combo.currentText()
        
        # 保存当前设置
        self.current_settings = {
            'font_size': self.font_size_combo.currentText(),
            'color_mode': self.color_mode_combo.currentText(),
            'preview_size': self.preview_size_combo.currentText()
        }
        
        # 根据屏幕类型设置默认参数，但保留用户的自定义设置
        if "OLED" in screen_type:
            # OLED模式：使用保存的设置或默认值
            if self.color_mode_combo.currentText() in ["16色", "256色", "真彩色"]:
                # 如果当前是TFT专用的颜色模式，则切换为OLED兼容的模式
                self.color_mode_combo.setCurrentText("单色")
            else:
                # 保留用户的颜色设置（如果兼容OLED）
                pass
            
            # 保留用户的字体大小设置，不强制切换
            # self.font_size_combo.setCurrentText("小(8px)")  # 注释掉强制设置
            
        elif "TFT" in screen_type:
            # TFT模式：使用保存的设置或默认值
            if self.color_mode_combo.currentText() == "单色":
                # 如果当前是单色模式，则切换为TFT推荐的颜色模式
                self.color_mode_combo.setCurrentText("16色")
            else:
                # 保留用户的颜色设置
                pass
            
            # 保留用户的字体大小设置，不强制切换
            # self.font_size_combo.setCurrentText("中(12px)")  # 注释掉强制设置
        
        # 更新预览
        self.on_screen_config_changed()
    
    def on_screen_config_changed(self):
        """屏幕配置改变时更新预览"""
        # 确保预览大小控件已传递
        self.preview.preview_size_combo = self.preview_size_combo
        
        # 获取所有颜色设置 - 从HEX输入框获取实际的颜色值
        font_color = self.font_color_hex.text().strip() if hasattr(self, 'font_color_hex') else "#FFFFFF"
        bg_color = self.bg_color_hex.text().strip() if hasattr(self, 'bg_color_hex') else "#004080"
        selected_bg = self.selected_bg_hex.text().strip() if hasattr(self, 'selected_bg_hex') else "#FFFFFF"
        selected_font = self.selected_font_hex.text().strip() if hasattr(self, 'selected_font_hex') else "#000000"
        
        # 如果HEX值为空，使用默认值
        if not font_color or not font_color.startswith('#'):
            font_color = "#FFFFFF"
        if not bg_color or not bg_color.startswith('#'):
            bg_color = "#004080"
        if not selected_bg or not selected_bg.startswith('#'):
            selected_bg = "#FFFFFF"
        if not selected_font or not selected_font.startswith('#'):
            selected_font = "#000000"
        
        # 传递所有颜色参数
        self.preview.set_screen_type(
            self.screen_type_combo.currentText(),
            self.color_mode_combo.currentText(),
            self.font_size_combo.currentText(),
            font_color,
            bg_color,
            selected_bg,
            selected_font
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
            color_mode = self.color_mode_combo.currentText()
            font_size = self.font_size_combo.currentText()
            
            # 更新预览屏幕尺寸
            self.preview.fb_w = width
            self.preview.fb_h = height
            
            # 重新创建framebuffer
            self.preview.framebuffer = QPixmap(width, height)
            
            # 根据屏幕类型设置颜色
            if "OLED" in screen_type:
                self.preview.bg_color = Qt.black
                self.preview.fg_color = QColor(0, 255, 0)  # OLED绿色
                self.preview.selected_bg_color = QColor(0, 255, 0)
                self.preview.selected_fg_color = Qt.black
            else:  # TFT
                self.preview.bg_color = QColor(0, 64, 128)  # 深蓝色
                self.preview.fg_color = Qt.white
                self.preview.selected_bg_color = QColor(255, 255, 255)
                self.preview.selected_fg_color = Qt.black
            
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
                        break
    
    # ---------------- 颜色选择器方法 ----------------
    def choose_color(self, color_type):
        """打开颜色选择器"""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtCore import Qt
        
        # 获取当前颜色
        if color_type == 'bg':
            current_color = QColor(0, 64, 128)  # 默认深蓝色
            if hasattr(self.preview, 'bg_color'):
                current_color = self.preview.bg_color
            btn = self.bg_color_btn
            hex_input = self.bg_color_hex
        elif color_type == 'font':
            current_color = Qt.white  # 默认白色
            if hasattr(self.preview, 'fg_color'):
                current_color = self.preview.fg_color
            btn = self.font_color_btn
            hex_input = self.font_color_hex
        elif color_type == 'selected_bg':
            current_color = Qt.white  # 默认白色
            if hasattr(self.preview, 'selected_bg_color'):
                current_color = self.preview.selected_bg_color
            btn = self.selected_bg_btn
            hex_input = self.selected_bg_hex
        elif color_type == 'selected_font':
            current_color = Qt.black  # 默认黑色
            if hasattr(self.preview, 'selected_fg_color'):
                current_color = self.preview.selected_fg_color
            btn = self.selected_font_btn
            hex_input = self.selected_font_hex
        else:
            return
        
        # 打开颜色选择器
        color = QColorDialog.getColor(current_color, self, f"选择{color_type}颜色")
        if color.isValid():
            # 更新按钮颜色
            btn.setStyleSheet(f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};")
            
            # 更新HEX输入框
            hex_input.setText(color.name().upper())
            
            # 更新预览
            self.on_screen_config_changed()
    
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
            
            # 更新预览
            self.on_screen_config_changed()
        except:
            pass  # 忽略无效的HEX输入
    
    # ---------------- 设置保存和加载 ----------------
    def save_settings(self):
        """保存当前设置到文件"""
        import json
        import os
        
        settings = {
            'screen_type': self.screen_type_combo.currentText(),
            'color_mode': self.color_mode_combo.currentText(),
            'font_size': self.font_size_combo.currentText(),
            'preview_size': self.preview_size_combo.currentText(),
            'bg_color': self.bg_color_hex.text().strip() if hasattr(self, 'bg_color_hex') else "#004080",
            'font_color': self.font_color_hex.text().strip() if hasattr(self, 'font_color_hex') else "#FFFFFF",
            'selected_bg': self.selected_bg_hex.text().strip() if hasattr(self, 'selected_bg_hex') else "#FFFFFF",
            'selected_font': self.selected_font_hex.text().strip() if hasattr(self, 'selected_font_hex') else "#000000",
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
                            
                            # 应用颜色模式
                            if hasattr(self, 'color_mode_combo') and 'color_mode' in self.current_settings:
                                self.color_mode_combo.blockSignals(True)
                                self.color_mode_combo.setCurrentText(self.current_settings['color_mode'])
                                self.color_mode_combo.blockSignals(False)
                                print(f"设置颜色模式: {self.current_settings['color_mode']}")
                            
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
                            
                            # 应用屏幕尺寸
                            if hasattr(self, 'screen_width_edit') and 'screen_width' in self.current_settings:
                                self.screen_width_edit.blockSignals(True)
                                self.screen_width_edit.setText(self.current_settings['screen_width'])
                                self.screen_width_edit.blockSignals(False)
                            if hasattr(self, 'screen_height_edit') and 'screen_height' in self.current_settings:
                                self.screen_height_edit.blockSignals(True)
                                self.screen_height_edit.setText(self.current_settings['screen_height'])
                                self.screen_height_edit.blockSignals(False)
                            
                            # 应用TFT颜色设置（如果是TFT模式）
                            if hasattr(self, 'screen_type_combo') and self.screen_type_combo.currentText() == "128x128 TFT":
                                if 'bg_color' in self.current_settings and hasattr(self, 'bg_color_hex'):
                                    self.bg_color_hex.blockSignals(True)
                                    self.bg_color_hex.setText(self.current_settings['bg_color'])
                                    self.bg_color_hex.blockSignals(False)
                                    print(f"设置背景颜色: {self.current_settings['bg_color']}")
                                if 'font_color' in self.current_settings and hasattr(self, 'font_color_hex'):
                                    self.font_color_hex.blockSignals(True)
                                    self.font_color_hex.setText(self.current_settings['font_color'])
                                    self.font_color_hex.blockSignals(False)
                                    print(f"设置字体颜色: {self.current_settings['font_color']}")
                                if 'selected_bg' in self.current_settings and hasattr(self, 'selected_bg_hex'):
                                    self.selected_bg_hex.blockSignals(True)
                                    self.selected_bg_hex.setText(self.current_settings['selected_bg'])
                                    self.selected_bg_hex.blockSignals(False)
                                    print(f"设置选中背景: {self.current_settings['selected_bg']}")
                                if 'selected_font' in self.current_settings and hasattr(self, 'selected_font_hex'):
                                    self.selected_font_hex.blockSignals(True)
                                    self.selected_font_hex.setText(self.current_settings['selected_font'])
                                    self.selected_font_hex.blockSignals(False)
                                    print(f"设置选中字体: {self.current_settings['selected_font']}")
                                    
                                    # 更新按钮颜色
                                    try:
                                        from PySide6.QtGui import QColor
                                        color = QColor(self.current_settings['selected_font'])
                                        if color.isValid():
                                            self.selected_font_btn.setStyleSheet(
                                                f"background-color: {color.name()}; color: {'white' if color.lightness() < 128 else 'black'};"
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
        def add_items(parent, node):
            twi = QTreeWidgetItem([node.name])
            twi.setData(0, Qt.UserRole, node)
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

    # ---------------- 菜单导航 ----------------
    def on_key(self,key):
        # 处理右键按下 - 进入子菜单或执行
        if key == "Right":
            visible = [c for c in self.preview.menu_root.children if c.visible]
            if self.preview.cursor_index < len(visible):
                node = visible[self.preview.cursor_index]
                if node.is_exec:
                    # 执行项
                    print(f"执行回调: {node.callback_name}")
                elif node.children and len(node.children) > 0:
                    # 进入子菜单
                    self.preview.menu_root = node
                    self.preview.cursor_index = 0  # 重置到第一项
                    print(f"进入子菜单: {node.name}")
                else:
                    print("该菜单项没有子菜单")
        # 处理左键按下 - 返回上级菜单
        elif key == "Left":
            if self.preview.menu_root.parent:
                # 保存当前菜单项的位置
                current_root = self.preview.menu_root
                current_root.cursor_pos = self.preview.cursor_index
                
                # 返回上级菜单
                self.preview.menu_root = self.preview.menu_root.parent
                
                # 在父菜单中找到当前子菜单的位置
                parent_visible = [c for c in self.preview.menu_root.children if c.visible]
                for i, child in enumerate(parent_visible):
                    if child == current_root:
                        self.preview.cursor_index = i
                        break
                else:
                    self.preview.cursor_index = 0
                print(f"返回上级菜单: {self.preview.menu_root.name}")
            else:
                print("已在根菜单，无法返回")
        # 处理上下键 - 导航菜单项
        else:
            visible = [c for c in self.preview.menu_root.children if c.visible]
            
            if key == "Up":
                self.preview.cursor_index = max(0, self.preview.cursor_index - 1)
            elif key == "Down":
                self.preview.cursor_index = min(len(visible) - 1, self.preview.cursor_index + 1)
            
            # 保存当前菜单项的位置
            self.preview.menu_root.cursor_pos = self.preview.cursor_index
        
        # 重新渲染菜单
        self.preview.render_menu()

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
        filename,_ = QFileDialog.getSaveFileName(self,"保存C代码","menu.c","C Files (*.c)")
        if not filename: return

        code = ["// 自动生成菜单代码 - U8G2", "#include <u8g2.h>", ""]
        code.append("// ---------------- 回调函数 ----------------")
        def gen_callbacks(node):
            for c in node.children:
                if c.is_exec:
                    cb = c.callback_name if c.callback_name else f"menu_cb_{c.id}"
                    code.append(f"void {cb}(void) {{")
                    code.append(f"    // TODO: 在此添加 {c.name} 的执行代码")
                    code.append("}\n")
                gen_callbacks(c)
        gen_callbacks(self.menu_root)

        code.append("typedef struct MenuItem {")
        code.append("  const char *name;")
        code.append("  uint8_t is_exec;")
        code.append("  uint8_t child_count;")
        code.append("  struct MenuItem *children;")
        code.append("  void (*callback)(void);")
        code.append("} MenuItem;\n")

        # 生成嵌套数组
        def gen_nodes(node):
            for c in node.children:
                if c.children:
                    gen_nodes(c)
            arr_name = f"{node.name.replace(' ','_')}_children"
            code.append(f"MenuItem {arr_name}[{len(node.children)}] = {{")
            for c in node.children:
                child_ptr = f"{c.name.replace(' ','_')}_children" if c.children else "NULL"
                cb_ptr = c.callback_name if c.is_exec else "NULL"
                code.append(f'  {{"{c.name}", {1 if c.is_exec else 0}, {len(c.children)}, {child_ptr}, {cb_ptr}}},')
            code.append("};\n")

        gen_nodes(self.menu_root)
        root_arr_name = f"{self.menu_root.name.replace(' ','_')}_children"
        code.append(f"MenuItem *menu_root = {root_arr_name};")

        with open(filename,"w",encoding="utf-8") as f:
            f.write("\n".join(code))
        print(f"C代码已导出: {filename}")

# ---------------- Main ----------------
if __name__=="__main__":
    app = QApplication([])
    w = MenuDesigner()
    w.show()
    app.exec()
