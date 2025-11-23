# MCU 菜单移植与使用说明（清晰版）

## 1. 目标
- 将导出的 `u8g2_code/` 加入工程后，适配按键输入（移植接口）即可使用菜单 UI；业务逻辑在回调文件中实现。

## 2. 前置条件
- 已集成 u8g2 库（支持你的屏幕控制器与 I2C/SPI 总线）。
- 工程可编译 C 源文件（HAL/LL/裸机均可）。

## 3. 导出目录结构
- `u8g2_code/menu/menu.h/.c`：菜单结构、根指针、绘制骨架
- `u8g2_code/fonts/ascii_font.h/.c`：ASCII 字库（按需）
- `u8g2_code/fonts/cjk_font.h/.c`：中文子集字库与绘制函数（按需）
- `u8g2_code/callbacks/callbacks.h/.c`：回调函数声明与空实现（用户填写）
- `u8g2_code/porting_interface.h/.c`：四键导航接口（光标与滚动）
- `u8g2_code/u8g2_bundle.h`：聚合头文件（一次性包含上述模块）

## 4. 快速开始（推荐流程）
1) 拷贝并编译：
- 必选：`menu/menu.c`、`porting_interface.c`
- 业务：`callbacks/callbacks.c`
- 按需：`fonts/ascii_font.c`、`fonts/cjk_font.c`
2) 头文件包含：
- `#include "u8g2_code/u8g2_bundle.h"`
3) 初始化与主循环：
```
menu_nav_init(&nav, menu_root);
menu_nav_on_key(&nav, key, visible_lines);
draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start);
```
4) 在 `callbacks/callbacks.c` 中为执行项函数填写业务逻辑。

## 5. 移植接口（四键导航）
- 键枚举：`MENU_KEY_UP`、`MENU_KEY_DOWN`、`MENU_KEY_ENTER`、`MENU_KEY_BACK`
- 状态：`MenuState{cursor, view_start}`
- 导航：`MenuNav{current, stack[16], depth, state}`
- API：
- `void menu_nav_init(MenuNav* nav, MenuItem* root)`
- `void menu_nav_on_key(MenuNav* nav, MenuKey key, uint8_t visible_lines)`
- 可视行数：`visible_lines = u8g2_GetDisplayHeight(&u8g2) / line_h`

## 6. 主循环示例
```
#include "u8g2_code/u8g2_bundle.h"

u8g2_t u8g2;
MenuNav nav;

void app_init(void) {
  /* 初始化 u8g2 与屏幕 */
  menu_nav_init(&nav, menu_root);
}

MenuKey read_key(void) {
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

## 7. 回调函数开发
- 文件：`u8g2_code/callbacks/callbacks.c`
- 命名：UI 中填写的回调名或 `menu_cb_<id>`。
- 示例：
```
void menu_cb_123(void) {}
```

## 8. 绘制与样式自定义
- 启用中文子集后，`draw_menu` 自动使用 `draw_text_mixed` 混合绘制。
- 当前行高亮示例：
```
/* u8g2_DrawBox(u8g2, 0, base_y + cursor * line_h - (line_h-1), u8g2_GetDisplayWidth(u8g2), line_h); */
```

## 9. 中文子集字库说明
- 仅导出菜单中实际出现的汉字与常用 CJK 标点。
- 提供：`cjk_bitmap_<px>[]`、`cjk_table_<px>[]`、`cjk_find_idx`、`draw_cjk_char`、`utf8_next`、`draw_text_mixed`。
- 字体来源与大小由 UI 设置决定；文本需为 UTF-8。

## 10. 常见问题与排查
- 链接错误：确认编译 `callbacks/callbacks.c`、`porting_interface.c`，并设置 `u8g2_code/` 为包含路径。
- 字体清晰度：OLED 建议较小像素并关闭抗锯齿；TFT 可开启抗锯齿。
- 中文显示异常：启用中文子集导出、包含 `cjk_font.*`，文本为 UTF-8。
- 滚动异常：检查 `visible_lines` 是否合理。

## 11. STM32 HAL 示例（I2C SSD1306）
```
#include "u8g2_code/u8g2_bundle.h"
#include "u8g2.h"

extern uint8_t u8x8_byte_hw_i2c(u8x8_t *u8x8, uint8_t msg, uint8_t arg_int, void *arg_ptr);
extern uint8_t u8x8_gpio_and_delay_stm32(u8x8_t *u8x8, uint8_t msg, uint8_t arg_int, void *arg_ptr);

u8g2_t u8g2; MenuNav nav;

void app_init(void) {
  u8g2_Setup_ssd1306_i2c_128x64_noname_f(&u8g2, U8G2_R0, u8x8_byte_hw_i2c, u8x8_gpio_and_delay_stm32);
  u8g2_SetI2CAddress(&u8g2, 0x78);
  u8g2_InitDisplay(&u8g2);
  u8g2_SetPowerSave(&u8g2, 0);
  menu_nav_init(&nav, menu_root);
}

MenuKey read_key(void) { return MENU_KEY_NONE; }

void app_loop(void) {
  MenuKey key = read_key();
  uint8_t line_h = 12;
  uint8_t visible_lines = u8g2_GetDisplayHeight(&u8g2) / line_h;
  menu_nav_on_key(&nav, key, visible_lines);
  draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start);
}
```

## 12. 提示
- 需要 SPI/TFT 示例或构建系统（Keil/IAR/CMake）包含设置示例时，可在此文档基础上继续扩展。

## 13. STM32 标准库示例（StdPeriph + 软件 I2C SSD1306）
- 硬件约定：
  - OLED I2C 软件模拟：SCL=PB6，SDA=PB7
  - 四键：UP=PA0，DOWN=PA1，ENTER=PA2，BACK=PA3（低电平按下）
- 依赖：`stm32f10x_*` 标准库、`u8g2`

```c
#include "stm32f10x.h"
#include "stm32f10x_rcc.h"
#include "stm32f10x_gpio.h"
#include "u8g2.h"
#include "u8g2_code/u8g2_bundle.h"

static void clock_init(void){
  RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB, ENABLE);
}

static void gpio_init(void){
  GPIO_InitTypeDef gi;
  gi.GPIO_Pin = GPIO_Pin_6 | GPIO_Pin_7; gi.GPIO_Speed = GPIO_Speed_50MHz; gi.GPIO_Mode = GPIO_Mode_Out_OD; GPIO_Init(GPIOB, &gi);
  GPIO_SetBits(GPIOB, GPIO_Pin_6 | GPIO_Pin_7);
  gi.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3; gi.GPIO_Speed = GPIO_Speed_50MHz; gi.GPIO_Mode = GPIO_Mode_IPU; GPIO_Init(GPIOA, &gi);
}

static void delay_us(uint32_t us){ volatile uint32_t n = us * 8; while(n--) __NOP(); }
static void delay_ms(uint32_t ms){ while(ms--) delay_us(1000); }

uint8_t u8x8_gpio_and_delay_stm32_std(u8x8_t* u8x8, uint8_t msg, uint8_t arg_int, void* arg_ptr){
  switch(msg){
    case U8X8_MSG_GPIO_AND_DELAY_INIT: return 1;
    case U8X8_MSG_DELAY_MILLI: delay_ms(arg_int); return 1;
    case U8X8_MSG_DELAY_10MICRO: delay_us(10); return 1;
    case U8X8_MSG_GPIO_I2C_CLOCK: if(arg_int) GPIO_SetBits(GPIOB,GPIO_Pin_6); else GPIO_ResetBits(GPIOB,GPIO_Pin_6); return 1;
    case U8X8_MSG_GPIO_I2C_DATA:  if(arg_int) GPIO_SetBits(GPIOB,GPIO_Pin_7); else GPIO_ResetBits(GPIOB,GPIO_Pin_7); return 1;
    case U8X8_MSG_GPIO_CS:
    case U8X8_MSG_GPIO_DC:
    case U8X8_MSG_GPIO_RESET: return 1;
    default: return 0;
  }
}

static MenuKey read_key(void){
  if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_0)==Bit_RESET) return MENU_KEY_UP;
  if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_1)==Bit_RESET) return MENU_KEY_DOWN;
  if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_2)==Bit_RESET) return MENU_KEY_ENTER;
  if(GPIO_ReadInputDataBit(GPIOA,GPIO_Pin_3)==Bit_RESET) return MENU_KEY_BACK;
  return MENU_KEY_NONE;
}

u8g2_t u8g2; MenuNav nav;

int main(void){
  clock_init(); gpio_init();
  u8g2_Setup_ssd1306_i2c_128x64_noname_f(&u8g2, U8G2_R0, u8x8_byte_sw_i2c, u8x8_gpio_and_delay_stm32_std);
  u8g2_InitDisplay(&u8g2); u8g2_SetPowerSave(&u8g2, 0);
  menu_nav_init(&nav, menu_root);
  while(1){
    MenuKey key = read_key();
    uint8_t line_h = 12; uint8_t visible_lines = u8g2_GetDisplayHeight(&u8g2)/line_h;
    menu_nav_on_key(&nav, key, visible_lines);
    u8g2_ClearBuffer(&u8g2);
    draw_menu(&u8g2, nav.current, nav.state.cursor, nav.state.view_start);
    u8g2_SendBuffer(&u8g2);
  }
}
```

说明：软件 I2C 便于快速移植；若需硬件 I2C，可改用 `u8x8_byte_hw_i2c` 并初始化 I2C1 外设与 AF 引脚。