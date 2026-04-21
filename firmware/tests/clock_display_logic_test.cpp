#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "clock_display_logic.h"

static void expect_true(bool condition, const char* message) {
  if (!condition) {
    fprintf(stderr, "%s\n", message);
    exit(1);
  }
}

static void expect_str_eq(const char* actual, const char* expected, const char* message) {
  if (strcmp(actual, expected) != 0) {
    fprintf(stderr, "%s: expected '%s' got '%s'\n", message, expected, actual);
    exit(1);
  }
}

int main() {
  char buf[16];

  clockFormatHm(buf, sizeof(buf), 9, 5);
  expect_str_eq(buf, "09:05", "valid hours and minutes should render normally");

  clockFormatHm(buf, sizeof(buf), -1, 42);
  expect_str_eq(buf, "--:--", "invalid hour should render as placeholder instead of unsigned garbage");

  clockFormatSeconds(buf, sizeof(buf), 42);
  expect_str_eq(buf, ":42", "valid seconds should render normally");

  clockFormatSeconds(buf, sizeof(buf), -1);
  expect_str_eq(buf, ":--", "invalid seconds should render as placeholder");

  clockFormatDateLine(buf, sizeof(buf), 4, 20);
  expect_str_eq(buf, "Apr 20", "valid month and date should render normally");

  clockFormatDateLine(buf, sizeof(buf), -1, 20);
  expect_str_eq(buf, "--- --", "invalid month should render as placeholder");

  return 0;
}
