# mcu_menu_designer_u8g2_final_complete.py
from PySide6.QtWidgets import (QApplication, QWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QFileDialog, QGroupBox, QComboBox)
from PySide6.QtGui import QPainter, QPixmap, QColor
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
    def __init__(self, fb_w=128, fb_h=64, font_px=8):
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
        if screen_type == "128x64 OLED":
            self.fb_w, self.fb_h = 128, 64
            self.base_font_px = 8
            self.max_lines = 8
            self.bg_color = Qt.black
            self.fg_color = QColor(0, 255, 0)  # OLED绿色
            self.selected_bg_color = QColor(0, 255, 0)
            self.selected_fg_color = Qt.black
        elif screen_type == "240x240 TFT":
            self.fb_w, self.fb_h = 240, 240
            self.base_font_px = 12
            self.max_lines = 16
            self.bg_color = QColor(0, 64, 128)  # 深蓝色
            self.fg_color = Qt.white
            self.selected_bg_color = QColor(255, 255, 255)
            self.selected_fg_color = Qt.black
        elif screen_type == "320x240 TFT":
            self.fb_w, self.fb_h = 320, 240
            self.base_font_px = 12
            self.max_lines = 16
            self.bg_color = QColor(0, 51, 102)  # 更深的蓝色
            self.fg_color = Qt.white
            self.selected_bg_color = QColor(255, 255, 255)
            self.selected_fg_color = Qt.black
        elif screen_type == "160x128 LCD":
            self.fb_w, self.fb_h = 160, 128
            self.base_font_px = 8
            self.max_lines = 14
            self.bg_color = QColor(240, 240, 240)  # 浅灰色
            self.fg_color = Qt.black
            self.selected_bg_color = Qt.black
            self.selected_fg_color = Qt.white
        else:  # 自定义
            self.fb_w, self.fb_h = 240, 240
            self.base_font_px = 10
            self.max_lines = 20
            self.bg_color = Qt.gray
            self.fg_color = Qt.white
            self.selected_bg_color = Qt.white
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
        if self.screen_type == "128x64 OLED":
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
        if self.screen_type == "128x64 OLED":
            painter.fillRect(frame_rect, QColor(40, 40, 40))
            painter.setPen(QColor(100, 100, 100))
            painter.drawRoundedRect(inner_rect.adjusted(-4, -4, 4, 4), 8, 8)
        elif "TFT" in self.screen_type:
            painter.fillRect(frame_rect, QColor(60, 60, 80))
            painter.setPen(QColor(100, 120, 140))
            painter.drawRoundedRect(inner_rect.adjusted(-4, -4, 4, 4), 12, 12)
        elif "LCD" in self.screen_type:
            painter.fillRect(frame_rect, QColor(200, 200, 200))
            painter.setPen(QColor(150, 150, 150))
            painter.drawRoundedRect(inner_rect.adjusted(-4, -4, 4, 4), 8, 8)
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
        if self.screen_type == "128x64 OLED":
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
        
        # 绘制滚动指示器
        if hasattr(self, 'show_scrollbar') and self.show_scrollbar:
            self._draw_scrollbar(painter, inner_rect, int_scale)

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
        scrollbar_color = QColor(60, 60, 60) if self.screen_type == "128x64 OLED" else QColor(100, 100, 100)
        painter.fillRect(int(scrollbar_x), int(scrollbar_y), int(scrollbar_width), int(scrollbar_height), scrollbar_color)
        
        # 计算滑块大小和位置
        total_ratio = self.max_lines / len(visible)
        thumb_height = max(20 * scale_factor, int(scrollbar_height * total_ratio))
        
        # 当前位置比例
        current_pos_ratio = self.current_page / ((len(visible) - 1) // self.max_lines + 1) if len(visible) > self.max_lines else 0
        thumb_y = scrollbar_y + int((scrollbar_height - thumb_height) * current_pos_ratio)
        
        # 绘制滑块
        thumb_color = QColor(80, 255, 80) if self.screen_type == "128x64 OLED" else QColor(150, 150, 255)
        painter.fillRect(int(scrollbar_x), int(thumb_y), int(scrollbar_width), int(thumb_height), thumb_color)

    def render_menu(self):
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
        
        # 绘制菜单项
        painter = QPainter(self.framebuffer)
        painter.setPen(self.fg_color)
        font = self._get_font()
        painter.setFont(font)
        
        # 设置渲染提示，提高文本清晰度
        # 对于像素级显示，禁用抗锯齿可能更清晰
        if self.screen_type == "128x64 OLED":
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.TextAntialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)  # 禁用平滑变换
        else:
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.TextAntialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)  # 启用平滑变换
        
        # 计算字符宽度和最大显示长度
        char_width = self.base_font_px * 0.6  # 估算字符宽度
        if self.screen_type == "128x64 OLED":
            max_name_length = 12  # OLED屏幕显示较短
        elif "TFT" in self.screen_type:
            max_name_length = 18  # TFT屏幕显示较长
        else:
            max_name_length = 15  # 其他屏幕
            
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
                # 绘制选中背景
                painter.fillRect(0, y - line_h, self.fb_w, line_h, self.selected_bg_color)
                painter.setPen(self.selected_fg_color)
                
                # 绘制选中项内容
                prefix = "►" if self.screen_type == "128x64 OLED" else "▶"
                suffix = " »" if not item.is_exec else ""
                text = f"{prefix} {indent}{display_name}{suffix}"
                # 使用更适合像素级显示的文本渲染方法
                if self.screen_type == "128x64 OLED":
                    # OLED使用精确的像素位置，使用整数坐标避免亚像素模糊
                    text_x = 2
                    text_y = y - 1  # 微调垂直位置
                    painter.drawText(text_x, text_y, text)
                else:
                    # 其他屏幕使用居中对齐
                    rect = painter.boundingRect(2, y - line_h, self.fb_w - 4, line_h, Qt.AlignLeft | Qt.AlignVCenter, text)
                    painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)
                
                # 绘制位置指示器（显示当前项位置）
                if max_lines < total:
                    pos_text = f"{idx+1}/{total}"
                    painter.setPen(self.selected_fg_color)
                    # 使用更好的文本渲染方法
                    rect = painter.boundingRect(self.fb_w - 30, y - line_h, 25, line_h, Qt.AlignRight | Qt.AlignVCenter, pos_text)
                    painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, pos_text)
            else:
                # 绘制普通项
                painter.setPen(self.fg_color)
                prefix = "  "
                suffix = " ▷" if not item.is_exec else "  "
                text = f"{prefix} {indent}{display_name}{suffix}"
                # 使用更适合像素级显示的文本渲染方法
                if self.screen_type == "128x64 OLED":
                    # OLED使用精确的像素位置，使用整数坐标避免亚像素模糊
                    text_x = 2
                    text_y = y - 1  # 微调垂直位置
                    painter.drawText(text_x, text_y, text)
                else:
                    # 其他屏幕使用居中对齐
                    rect = painter.boundingRect(2, y - line_h, self.fb_w - 4, line_h, Qt.AlignLeft | Qt.AlignVCenter, text)
                    painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, text)
        
        # 绘制页码信息（如果有多页）
        if max_lines < total:
            page_text = f"第 {self.current_page + 1}/{(total - 1) // max_lines + 1} 页"
            painter.setPen(self.fg_color)
            # 使用更好的文本渲染方法
            rect = painter.boundingRect(0, self.fb_h - 20, self.fb_w, 15, Qt.AlignCenter, page_text)
            painter.drawText(rect, Qt.AlignCenter, page_text)
        
        painter.end()
        self.update()

    def _get_font(self):
        """获取合适的字体"""
        from PySide6.QtGui import QFont
        # 使用更适合像素级显示的字体
        if self.screen_type == "128x64 OLED":
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

        # 根菜单
        self.menu_root = MenuItem("根菜单", is_exec=False)
        self.menu_root.add_child(MenuItem("系统设置"))
        self.menu_root.add_child(MenuItem("数据显示"))
        self.menu_root.add_child(MenuItem("设备控制"))
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
        self.screen_type_combo.addItems(["128x64 OLED", "240x240 TFT", "320x240 TFT", "160x128 LCD", "自定义"])
        self.screen_type_combo.currentTextChanged.connect(self.on_screen_type_changed)
        screen_type_layout.addWidget(self.screen_type_combo)
        screen_type_layout.addStretch()
        
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
        """屏幕类型改变时更新配置"""
        screen_type = self.screen_type_combo.currentText()
        
        # 根据屏幕类型设置默认参数
        if screen_type == "128x64 OLED":
            self.color_mode_combo.setCurrentText("单色")
            self.font_size_combo.setCurrentText("小(8px)")
        elif screen_type in ["240x240 TFT", "320x240 TFT"]:
            self.color_mode_combo.setCurrentText("16色")
            self.font_size_combo.setCurrentText("中(12px)")
        elif screen_type == "160x128 LCD":
            self.color_mode_combo.setCurrentText("单色")
            self.font_size_combo.setCurrentText("小(8px)")
        
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
