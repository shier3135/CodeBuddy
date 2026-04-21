#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

static const char CLOCK_MON[][4] = {
  "Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"
};

static const char CLOCK_DOW[][4] = {"Sun","Mon","Tue","Wed","Thu","Fri","Sat"};

inline bool clockValueInRange(int value, int min_value, int max_value) {
  return value >= min_value && value <= max_value;
}

inline const char* clockMonthLabel(int month) {
  return clockValueInRange(month, 1, 12) ? CLOCK_MON[month - 1] : "---";
}

inline const char* clockWeekdayLabel(int weekday) {
  return clockValueInRange(weekday, 0, 6) ? CLOCK_DOW[weekday] : "---";
}

inline void clockFormatHm(char* out, size_t size, int hours, int minutes) {
  if (!clockValueInRange(hours, 0, 23) || !clockValueInRange(minutes, 0, 59)) {
    snprintf(out, size, "--:--");
    return;
  }
  snprintf(out, size, "%02d:%02d", hours, minutes);
}

inline void clockFormatSeconds(char* out, size_t size, int seconds) {
  if (!clockValueInRange(seconds, 0, 59)) {
    snprintf(out, size, ":--");
    return;
  }
  snprintf(out, size, ":%02d", seconds);
}

inline void clockFormatDateLine(char* out, size_t size, int month, int date) {
  if (!clockValueInRange(month, 1, 12) || !clockValueInRange(date, 1, 31)) {
    snprintf(out, size, "--- --");
    return;
  }
  snprintf(out, size, "%s %02d", clockMonthLabel(month), date);
}

inline void clockFormatWeekDateLine(char* out, size_t size, int weekday, int month, int date) {
  if (!clockValueInRange(month, 1, 12) || !clockValueInRange(date, 1, 31)) {
    snprintf(out, size, "%s --- --", clockWeekdayLabel(weekday));
    return;
  }
  snprintf(out, size, "%s %s %02d", clockWeekdayLabel(weekday), clockMonthLabel(month), date);
}
