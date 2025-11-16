# mcu_menu_designer_u8g2_final_complete.py
from PySide6.QtWidgets import (QApplication, QWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QGroupBox, QComboBox)
from PySide6.QtGui import QPainter, QPixmap, QColor, QFont
from PySide6.QtCore import Qt

# ---------------- Menu 数据结构 ----------------
class MenuItem:
    _id_counter = 1
    def __init__(self, name="菜单项", is_exec=True, visible=True, parent=None):
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

    def set_screen_type(self, screen_type, color_mode="单色", font_size="小(8px)"):
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
            self.bg_color = QColor(0, 64, 128)  # 深蓝色
            self.fg_color = Qt.white
            self.selected_bg_color = QColor(255, 255, 255)
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
                
                # 绘制选中项内容
                prefix = "►" if "OLED" in self.screen_type else "▶"
                suffix = " »" if not item.is_exec else ""
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
                suffix = " ▷" if not item.is_exec else "  "
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
                type_text = "▶ 子菜单"
            
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
        
        # 保存当前设置状态，避免切换时丢失
        self.current_settings = {
            'font_size': '中(12px)',
            'color_mode': '单色',
            'preview_size': '放大2倍'
        }

        # 根菜单
        self.menu_root = MenuItem("根菜单", is_exec=False)
        self.menu_root.add_child(MenuItem("系统设置"))
        self.menu_root.add_child(MenuItem("数据显示"))
        self.menu_root.add_child(MenuItem("设备控制"))
        self.menu_root.add_child(MenuItem("通信设置"))
        self.menu_root.add_child(MenuItem("时间日期"))
        self.menu_root.add_child(MenuItem("网络配置"))
        self.menu_root.add_child(MenuItem("安全设置"))
        self.menu_root.add_child(MenuItem("用户管理"))
        self.menu_root.add_child(MenuItem("日志记录"))
        self.menu_root.add_child(MenuItem("系统信息"))
        self.menu_root.add_child(MenuItem("诊断工具"))
        self.menu_root.add_child(MenuItem("固件更新"))
        self.menu_root.add_child(MenuItem("备份恢复"))
        self.menu_root.add_child(MenuItem("工厂重置"))
        self.current_node = self.menu_root

        # 主布局
        main_layout = QHBoxLayout(self)

        # 左侧树控件
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("菜单结构")
        self.tree.itemClicked.connect(self.on_tree_select)
        self.refresh_tree()
        left_layout.addWidget(self.tree)

        # 中间属性编辑
        prop_group = QGroupBox("菜单项属性")
        prop_layout = QVBoxLayout(prop_group)

        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self.update_name)
        prop_layout.addWidget(QLabel("菜单名称"))
        prop_layout.addWidget(self.name_edit)

        self.is_exec_btn = QPushButton("切换执行/子菜单")
        self.is_exec_btn.clicked.connect(self.toggle_exec)
        prop_layout.addWidget(self.is_exec_btn)

        self.callback_edit = QLineEdit()
        prop_layout.addWidget(QLabel("回调函数名 (执行菜单有效)"))
        prop_layout.addWidget(self.callback_edit)
        self.callback_edit.editingFinished.connect(self.update_callback)

        self.add_btn = QPushButton("添加子菜单")
        self.add_btn.clicked.connect(self.add_menu)
        prop_layout.addWidget(self.add_btn)

        self.del_btn = QPushButton("删除菜单")
        self.del_btn.clicked.connect(self.del_menu)
        prop_layout.addWidget(self.del_btn)

        prop_layout.addWidget(QLabel(" "))
        self.export_btn = QPushButton("导出完整U8G2 C代码")
        self.export_btn.clicked.connect(self.export_code)
        prop_layout.addWidget(self.export_btn)
        prop_layout.addStretch()
        
        left_layout.addWidget(prop_group)
        main_layout.addWidget(left_widget, 1)

        # 右侧预览区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 屏幕配置组
        screen_config_group = QGroupBox("屏幕配置")
        screen_config_layout = QVBoxLayout(screen_config_group)
        
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
        self.apply_size_btn = QPushButton("应用尺寸")
        self.apply_size_btn.clicked.connect(self.on_apply_screen_size)
        screen_size_layout.addWidget(self.apply_size_btn)
        screen_size_layout.addStretch()
        
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
        self.font_size_combo.setCurrentText("中(12px)")  # 设置默认为12px
        self.font_size_combo.currentTextChanged.connect(self.on_screen_config_changed)
        font_size_layout.addWidget(self.font_size_combo)
        font_size_layout.addStretch()
        
        # 预览窗口大小设置
        preview_size_layout = QHBoxLayout()
        preview_size_layout.addWidget(QLabel("预览大小:"))
        self.preview_size_combo = QComboBox()
        self.preview_size_combo.addItems(["实际大小", "放大1.5倍", "放大2倍", "放大3倍"])
        self.preview_size_combo.setCurrentText("放大2倍")
        self.preview_size_combo.currentTextChanged.connect(self.on_preview_size_changed)
        preview_size_layout.addWidget(self.preview_size_combo)
        preview_size_layout.addStretch()
        
        screen_config_layout.addLayout(screen_type_layout)
        screen_config_layout.addLayout(screen_size_layout)
        screen_config_layout.addLayout(color_mode_layout)
        screen_config_layout.addLayout(font_size_layout)
        screen_config_layout.addLayout(preview_size_layout)
        right_layout.addWidget(screen_config_group)

        # 菜单预览组
        preview_group = QGroupBox("菜单预览")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        
        # 创建预览控件
        self.preview = MenuPreview()
        self.preview.preview_size_combo = self.preview_size_combo  # 传递预览大小控件
        self.preview.set_screen_type(
            self.screen_type_combo.currentText(),
            self.color_mode_combo.currentText(),
            self.font_size_combo.currentText()
        )
        self.preview.menu_root = self.menu_root
        self.preview.render_menu()
        preview_layout.addWidget(self.preview, 1)
        
        # 按键模拟
        keys_group = QGroupBox("按键模拟")
        keys_layout = QVBoxLayout(keys_group)
        
        # 主按键区域
        main_key_layout = QHBoxLayout()
        
        # 四键模式：上、下、确认、返回
        self.key_up_btn = QPushButton("↑ 上")
        self.key_down_btn = QPushButton("↓ 下")
        self.key_enter_btn = QPushButton("↵ 确认")
        self.key_back_btn = QPushButton("← 返回")
        
        self.key_up_btn.clicked.connect(lambda: self.on_key("Up"))
        self.key_down_btn.clicked.connect(lambda: self.on_key("Down"))
        self.key_enter_btn.clicked.connect(lambda: self.on_key("Enter"))
        self.key_back_btn.clicked.connect(lambda: self.on_key("Back"))
        
        main_key_layout.addWidget(self.key_up_btn)
        main_key_layout.addWidget(self.key_down_btn)
        main_key_layout.addWidget(self.key_enter_btn)
        main_key_layout.addWidget(self.key_back_btn)
        
        keys_layout.addLayout(main_key_layout)
        preview_layout.addWidget(keys_group)
        
        right_layout.addWidget(preview_group)
        main_layout.addWidget(right_widget, 1)

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
        self.preview.set_screen_type(
            self.screen_type_combo.currentText(),
            self.color_mode_combo.currentText(),
            self.font_size_combo.currentText()
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
        self.name_edit.setText(node.name)
        self.callback_edit.setText(node.callback_name)

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
            self.refresh_tree()
            self.preview.render_menu()

    def add_menu(self):
        if self.current_node:
            new_node = MenuItem("新菜单")
            self.current_node.add_child(new_node)
            self.refresh_tree()
            self.preview.render_menu()

    def del_menu(self):
        if self.current_node and self.current_node.parent:
            self.current_node.parent.children.remove(self.current_node)
            self.current_node = self.current_node.parent
            self.refresh_tree()
            self.preview.render_menu()

    # ---------------- 菜单导航 ----------------
    def on_key(self,key):
        visible = [c for c in self.preview.menu_root.children if c.visible]
        cur_root = self.preview.menu_root
        
        if key=="Up":
            self.preview.cursor_index = max(0,self.preview.cursor_index-1)
            cur_root.cursor_pos = self.preview.cursor_index
        elif key=="Down":
            self.preview.cursor_index = min(len(visible)-1,self.preview.cursor_index+1)
            cur_root.cursor_pos = self.preview.cursor_index
        elif key=="Enter":
            idx = self.preview.cursor_index
            if idx<len(visible):
                node = visible[idx]
                if node.is_exec:
                    print(f"执行回调: {node.callback_name}")
                elif node.children:
                    self.preview.menu_root = node
                    self.preview.cursor_index = node.cursor_pos
        elif key=="Back":
            if self.preview.menu_root.parent:
                self.preview.menu_root.cursor_pos = self.preview.cursor_index
                self.preview.menu_root = self.preview.menu_root.parent
                self.preview.cursor_index = self.preview.menu_root.cursor_pos
        self.preview.render_menu()

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
