# 📘 MUI 菜单移植与使用说明（清晰版）

## 0. 概览
- 目标：将导出的 `MUI/` 直接加入 MCU 工程，快速得到与 UI 预览一致的菜单样式与交互。
- 两种导出模式：
  - 依赖 U8G2（未勾选“导出不依赖U8G2的代码”）：生成 `MUI/menu/`、`MUI/fonts/`、`MUI/callbacks/`、`MUI/porting_interface.*`、`MUI/mui_bundle.h`
  - 裸机（勾选该选项）：生成 `MUI/menu_bare.*`、`MUI/port/*.c/.h`、`MUI/port/stm32_std/*.c`、`MUI/examples/example_bare.c`

---

## 1. 📦 目录结构
- 依赖 U8G2 导出：
  - `MUI/menu/menu.h/.c`：菜单结构与绘制骨架
  - `MUI/fonts/ascii_font.h/.c`、`MUI/fonts/cjk_font.h/.c`：ASCII/中文子集字库（按需）
  - `MUI/callbacks/callbacks.h/.c`：回调函数声明与空实现（用户填写）
  - `MUI/porting_interface.h/.c`：四键导航接口（光标与滚动）
  - `MUI/mui_bundle.h`：聚合头，一次性包含上述模块
- 裸机导出：
  - `MUI/menu/menu_bare.h/.c`：菜单结构、导航状态与渲染
  - `MUI/port/gfx_port.h/.c`：图形接口（含 `gfx_width/gfx_height`，默认 128×64）
  - `MUI/port/input_port.h/.c`：按键接口（返回 `MenuKey`）
  - `MUI/port/stm32_std/gfx_port_stm32_std.c`、`input_port_stm32_std.c`：STM32 StdPeriph 参考实现（SSD1306 I2C）
  - `MUI/examples/example_bare.c`：最小运行示例

---

## 2. ✅ 快速集成
- 依赖 U8G2：
  - 加入 `MUI/`，编译 `menu/`、`porting_interface.*`、`callbacks/`，按需编译 `fonts/`
  - 代码包含：`#include "MUI/mui_bundle.h"`
  - 初始化与循环：
    - `menu_nav_init(&nav, menu_root)`
    - `menu_nav_on_key(&nav, key, visible_lines)`
    - `draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start)`
- 裸机：
  - 加入 `MUI/`，编译 `menu/menu_bare.c`、`port/*.c`、`examples/example_bare.c`
  - 入口示例（已生成）：
```c
#include "MUI/menu/menu_bare.h"
#include "MUI/port/gfx_port.h"
#include "MUI/port/input_port.h"
int main(void){ gfx_init(); mui_nav_init(); for(;;){ MenuKey k=input_port_read(); mui_nav_on_key((uint8_t)k); mui_anim_tick(16); draw_menu_bare(mui_get_cursor(), mui_get_view_start()); } }
```

---

## 3. 🧰 接口说明
- 依赖 U8G2：
  - 导航：`MenuKey`、`MenuState`、`MenuNav`；`menu_nav_init`、`menu_nav_on_key`
  - 绘制：`draw_menu(u8g2, root, cursor, view_start)`（预览一致的骨架）
- 裸机：
  - 导航：`mui_nav_init`、`mui_nav_on_key(uint8_t)`（1=UP、2=DOWN、3=ENTER、4=BACK）
  - 动画：`mui_anim_tick(int dt_ms)`（建议每帧 16ms）
  - 状态：`mui_get_cursor`、`mui_get_view_start`
  - 图形：`gfx_init/clear/send/draw_pixel/fill_rect/draw_bitmap_1bpp/draw_text_mixed`、`gfx_width/gfx_height`

---

## 4. 🎨 样式与动画一致性（裸机）
- 当前行高亮：全宽填充条（与预览一致）
- 右侧滚动条：轨道与滑块高度/位置按总项与可视行数计算
- 底部导航文案：`< 上/下 选择  确认 >`
- 滑动动画：
  - 视窗变化时触发过渡：`off = from + (to - from) * ease(progress)`
  - 缓动：`ease(t) = t*t*(3-2t)`；默认动画时长 `g_anim_ms=140ms`
  - 每帧推进：`mui_anim_tick(16)`（约 60 FPS）

---

## 5. 🔌 STM32 StdPeriph 参考实现（SSD1306 I2C）
- `MUI/port/stm32_std/gfx_port_stm32_std.c`：
  - 初始化 `GPIOA/GPIOB/I2C1`、SSD1306 启动序列、帧缓与刷新
  - 画点/位图绘制、ASCII/中文子集混排文本
- `MUI/port/stm32_std/input_port_stm32_std.c`：
  - `PA0..PA3` 上拉输入，低电平按下，返回 `MenuKey`

---

## 6. 🧭 调优建议
- 屏幕分辨率：修改 `gfx_width/gfx_height` 为你的实际尺寸（如 240×240）
- 行高与基线：在 `menu_bare.c` 中调整 `line_h/base_y/bottom_h` 保持对齐与布局一致
- 字库：导出时勾选 ASCII/中文子集以匹配预览字体；若空间有限，可只启用必要子集
- 动画：可调整 `g_anim_ms` 以改变过渡速度；若 MCU 性能有限，可降低帧率（如 `mui_anim_tick(20~33)`）

---

## 7. ❓ 常见问题与排查
- 链接错误：确认已编译 `callbacks/callbacks.c` 或 `menu_bare.c` 与 `port/*.c`，并设置 `MUI/` 为包含路径
- 字体清晰度：OLED 建议较小像素并关闭抗锯齿；TFT 可开启抗锯齿
- 中文显示异常：启用中文子集导出、工程包含 `cjk_font.*`，文本使用 UTF-8
- 滚动异常：检查 `gfx_height/line_h/bottom_h`，确保可视行数合理

---

## 8. 🛠️ STM32 标准库（裸机）移植与使用示例

### 8.1 文件选择
- 源文件加入工程：
  - `MUI/menu/menu_bare.c`
  - `MUI/port/stm32_std/gfx_port_stm32_std.c`
  - `MUI/port/stm32_std/input_port_stm32_std.c`
  - 如需中文/ASCII 字库：导出时勾选相应选项，生成的位图与查表在 `MUI/port/gfx_port.c` 中被包含或组合

### 8.2 头文件包含
- 源文件顶部包含：
```c
#include "MUI/menu/menu_bare.h"
#include "MUI/port/gfx_port.h"
#include "MUI/port/input_port.h"
```

### 8.3 初始化与主循环
```c
int main(void){
  gfx_init();
  mui_nav_init();
  for(;;){
    MenuKey k = input_port_read();
    mui_nav_on_key((uint8_t)k);
    mui_anim_tick(16);
    draw_menu_bare(mui_get_cursor(), mui_get_view_start());
  }
  return 0;
}
```

### 8.4 I2C OLED 与按键引脚（默认参考）
- I2C1：`PB6=SCL`、`PB7=SDA`
- 按键：`PA0=UP`、`PA1=DOWN`、`PA2=ENTER`、`PA3=BACK`（上拉，低电平按下）
- 可在 `MUI/port/stm32_std/gfx_port_stm32_std.c` 与 `input_port_stm32_std.c` 中调整引脚与外设初始化

### 8.5 编译清单（示例）
- 将以下文件加入工程并编译：
  - `MUI/menu/menu_bare.c`
  - `MUI/port/stm32_std/gfx_port_stm32_std.c`
  - `MUI/port/stm32_std/input_port_stm32_std.c`
  - 如需字库：`MUI/port/gfx_port.c`

### 8.6 行为与样式校验
- 按键：上/下滚动、越界触发视窗移动；确认执行回调函数；返回占位。
- 样式：当前行高亮、右侧滚动条与底部文案；滑动动画与预览一致的缓动。

---

## 9. 🧪 U8G2 模式移植与使用示例（STM32）

### 9.1 文件选择
- 源文件加入工程：
  - `MUI/menu/menu.c`
  - `MUI/porting_interface.c`
  - `MUI/callbacks/callbacks.c`
  - 如需字库：`MUI/fonts/ascii_font.c`、`MUI/fonts/cjk_font.c`

### 9.2 头文件包含
- 源文件顶部包含（推荐）：
```c
#include "MUI/mui_bundle.h"
#include "u8g2.h"
```
- 或者分别包含：`menu/menu.h`、`porting_interface.h`、`callbacks/callbacks.h`，并按需包含 `fonts/cjk_font.h`

### 9.3 初始化与主循环（示例：SSD1306 I2C + 软件 I2C）
```c
#include "MUI/mui_bundle.h"
#include "u8g2.h"

extern uint8_t u8x8_byte_sw_i2c(u8x8_t*, uint8_t, uint8_t, void*);
extern uint8_t u8x8_gpio_and_delay_stm32_std(u8x8_t*, uint8_t, uint8_t, void*); // 你的 GPIO/延时适配

u8g2_t u8g2;
MenuNav nav;

int main(void){
  // 初始化 u8g2（根据屏幕与总线选择合适的 Setup）
  u8g2_Setup_ssd1306_i2c_128x64_noname_f(&u8g2, U8G2_R0, u8x8_byte_sw_i2c, u8x8_gpio_and_delay_stm32_std);
  u8g2_InitDisplay(&u8g2);
  u8g2_SetPowerSave(&u8g2, 0);

  // 菜单导航初始化
  menu_nav_init(&nav, menu_root);

  for(;;){
    MenuKey k = MENU_KEY_NONE; // 替换为你的按键读取
    menu_nav_on_key(&nav, k, u8g2_GetDisplayHeight(&u8g2)/12);
    u8g2_ClearBuffer(&u8g2);
    draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start);
    u8g2_SendBuffer(&u8g2);
  }
}
```

### 9.4 使用要点
- Setup 与控制器：根据你的屏幕选择 `u8g2_Setup_*`（I2C/SPI、控制器型号）；若使用硬件 I2C，替换为 `u8x8_byte_hw_i2c`
- 按键：使用你的 GPIO 读取映射为 `MenuKey`；可沿用裸机示例中的输入读取逻辑
- 字库：若启用中文子集，确保编译并链接 `MUI/fonts/cjk_font.c`，文本需为 UTF-8