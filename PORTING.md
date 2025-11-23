# MCU 菜单移植与使用说明

## 导出文件结构

导出目录选择后，会生成 `u8g2_code` 总文件夹：

- `u8g2_code/menu/menu.h`：菜单结构与 `menu_root` 声明、`draw_menu` 原型
- `u8g2_code/menu/menu.c`：菜单嵌套数组、空回调实现、`draw_menu` 绘制骨架
- `u8g2_code/fonts/ascii_font.h/.c`：ASCII 字体数组（可选）
- `u8g2_code/fonts/cjk_font.h/.c`：中文子集字库与绘制函数（可选）
- `u8g2_code/porting_interface.h/.c`：四键导航移植接口（光标与滚动）

## 编译集成

1. 将 `u8g2_code` 下的 `menu/` 必选加入工程；若启用中文子集或 ASCII 字库，加入 `fonts/`；加入 `porting_interface.*`。
2. 在代码中包含：
   - `#include "u8g2_code/menu/menu.h"`
   - 启用中文：`#include "u8g2_code/fonts/cjk_font.h"`
   - 导航接口：`#include "u8g2_code/porting_interface.h"`

## 四键导航接口

`u8g2_code/porting_interface.h` 定义：

- 键枚举：`MENU_KEY_UP`、`MENU_KEY_DOWN`、`MENU_KEY_ENTER`、`MENU_KEY_BACK`
- 状态与导航：`MenuState{cursor,view_start}`、`MenuNav{current,stack,depth,state}`
- 初始化：`void menu_nav_init(MenuNav* nav, MenuItem* root)`
- 按键处理：`void menu_nav_on_key(MenuNav* nav, MenuKey key, uint8_t visible_lines)`

## 使用示例

初始化与主循环：

```c
u8g2_t u8g2;
MenuNav nav;
menu_nav_init(&nav, menu_root);

for(;;){
  MenuKey key = MENU_KEY_NONE;
  if (key_up_pressed()) key = MENU_KEY_UP;
  else if (key_down_pressed()) key = MENU_KEY_DOWN;
  else if (key_enter_pressed()) key = MENU_KEY_ENTER;
  else if (key_back_pressed()) key = MENU_KEY_BACK;

  uint8_t line_h = 12;
  uint8_t visible_lines = u8g2_GetDisplayHeight(&u8g2) / line_h;
  menu_nav_on_key(&nav, key, visible_lines);

  draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start);
}
```

## 绘制说明

- `menu/menu.c` 的 `draw_menu`：
  - 默认使用 `u8g2_font_6x10_tf` 渲染 ASCII；
  - 若启用中文子集，自动调用 `draw_text_mixed(u8g2, txt, x, y)` 混合绘制；
- 如需高亮当前行或页导航，可基于 `cursor/view_start` 在该函数中绘制背景条或箭头。

## 中文子集字库

- 仅导出菜单中实际使用的汉字与常用 CJK 标点，减少固件体积；
- 提供：
  - `cjk_bitmap_<px>[]` 与 `cjk_table_<px>[]`（码点、位图偏移、宽高）；
  - `cjk_find_idx`、`draw_cjk_char`、`utf8_next`、`draw_text_mixed`；
- 字体来源与大小由 UI 中的“默认字体族”“字体大小”决定；请注意字体许可。

## 键值映射建议

- 上/下/确认/返回分别映射到 `MENU_KEY_UP/DOWN/ENTER/BACK`；
- 若硬件为左/右/确认/取消，可将左/右映射到上/下。

## 常见问题

- 水平滚动条：UI 已禁用配置页水平滚动；若仍出现，请增加右侧面板宽度或窗口宽度。
- 字库大小：如固件空间有限，可关闭 ASCII 或中文子集导出，或改用压缩位图策略。

## STM32 HAL 移植示例（I2C OLED）

依赖：HAL、u8g2、导出的 `u8g2_code`。

初始化与主循环：

```c
#include "u8g2_code/menu/menu.h"
#include "u8g2_code/porting_interface.h"
#include "u8g2.h"

u8g2_t u8g2;
MenuNav nav;

extern uint8_t u8x8_byte_hw_i2c(u8x8_t *u8x8, uint8_t msg, uint8_t arg_int, void *arg_ptr);
extern uint8_t u8x8_gpio_and_delay_stm32(u8x8_t *u8x8, uint8_t msg, uint8_t arg_int, void *arg_ptr);

void app_init(void) {
  u8g2_Setup_ssd1306_i2c_128x64_noname_f(&u8g2, U8G2_R0, u8x8_byte_hw_i2c, u8x8_gpio_and_delay_stm32);
  u8g2_SetI2CAddress(&u8g2, 0x78);
  u8g2_InitDisplay(&u8g2);
  u8g2_SetPowerSave(&u8g2, 0);
  menu_nav_init(&nav, menu_root);
}

static MenuKey read_key(void) {
  if (HAL_GPIO_ReadPin(KEY_UP_GPIO_Port, KEY_UP_Pin) == GPIO_PIN_RESET) return MENU_KEY_UP;
  if (HAL_GPIO_ReadPin(KEY_DOWN_GPIO_Port, KEY_DOWN_Pin) == GPIO_PIN_RESET) return MENU_KEY_DOWN;
  if (HAL_GPIO_ReadPin(KEY_OK_GPIO_Port, KEY_OK_Pin) == GPIO_PIN_RESET) return MENU_KEY_ENTER;
  if (HAL_GPIO_ReadPin(KEY_BACK_GPIO_Port, KEY_BACK_Pin) == GPIO_PIN_RESET) return MENU_KEY_BACK;
  return MENU_KEY_NONE;
}

void app_loop(void) {
  MenuKey key = read_key();
  uint8_t line_h = 12;
  uint8_t visible_lines = u8g2_GetDisplayHeight(&u8g2) / line_h;
  menu_nav_on_key(&nav, key, visible_lines);
  draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start);
}
```

中文子集集成：

```c
#include "u8g2_code/fonts/cjk_font.h"
```

SPI 屏幕或不同控制器：调整 `u8g2_Setup_*` 与总线回调。