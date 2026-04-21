#pragma once

#include <M5Unified.h>

using TFT_eSprite = M5Canvas;
using RTC_TimeTypeDef = m5::rtc_time_t;
using RTC_DateTypeDef = m5::rtc_date_t;

#define GetTime getTime
#define GetDate getDate
#define SetTime setTime
#define SetDate setDate
#define Init init
#define Beep Speaker
#define Hours hours
#define Minutes minutes
#define Seconds seconds
#define Month month
#define Date date
#define WeekDay weekDay

inline uint8_t compatBrightnessPercentToDisplay(int percent) {
  if (percent < 0) percent = 0;
  if (percent > 100) percent = 100;
  return (uint8_t)((percent * 255) / 100);
}

inline void compatSetBrightnessPercent(int percent) {
  M5.Display.setBrightness(compatBrightnessPercentToDisplay(percent));
}

inline void compatSetDisplayEnabled(bool enabled) {
  if (enabled) {
    M5.Display.wakeup();
  } else {
    M5.Display.sleep();
  }
}

inline int compatBatteryVoltageMv() {
  return M5.Power.getBatteryVoltage();
}

inline int compatBatteryCurrentMa() {
  return M5.Power.getBatteryCurrent();
}

inline int compatVbusVoltageMv() {
  return M5.Power.getVBUSVoltage();
}

inline int compatPowerKeyState() {
  return M5.Power.getKeyState();
}

inline void compatPowerOff() {
  M5.Power.powerOff();
}
