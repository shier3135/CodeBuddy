#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "utf8_text_logic.h"

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
  {
    char out[5];
    utf8CopyTruncate(out, "你好ab");
    expect_str_eq(out, "你", "truncate should not split a Chinese codepoint");
  }

  {
    char out[7];
    utf8CopyTruncate(out, "abc你好");
    expect_str_eq(out, "abc你", "truncate should keep the last whole UTF-8 codepoint that fits");
  }

  {
    expect_true(utf8DisplayCells("ab世界") == 6, "display width should treat Chinese codepoints as double-width");
    expect_true(utf8ContainsNonAscii("批准"), "Chinese text should be detected as non-ASCII");
    expect_true(!utf8ContainsNonAscii("approve"), "plain ASCII text should stay ASCII");
  }

  {
    char rows[3][16] = {};
    uint8_t got = utf8WrapInto("你好世界和平", rows, 3, 4, false);
    expect_true(got == 3, "Chinese text should wrap into multiple rows by display width");
    expect_str_eq(rows[0], "你好", "row 0 should keep whole Chinese glyphs");
    expect_str_eq(rows[1], "世界", "row 1 should keep whole Chinese glyphs");
    expect_str_eq(rows[2], "和平", "row 2 should keep whole Chinese glyphs");
  }

  {
    char rows[2][16] = {};
    uint8_t got = utf8WrapInto("tool 批准 prompt", rows, 2, 10, true);
    expect_true(got == 2, "mixed text should wrap into two rows");
    expect_str_eq(rows[0], "tool 批准", "first row should keep the mixed phrase intact when it fits");
    expect_str_eq(rows[1], " prompt", "continuation row should keep the leading indent");
  }

  {
    char rows[2][8] = {};
    uint8_t got = utf8WrapInto("你好啊", rows, 2, 6, false);
    expect_true(got == 2, "row byte capacity should force a safe wrap before splitting UTF-8");
    expect_str_eq(rows[0], "你好", "small row buffers should still end on a UTF-8 boundary");
    expect_str_eq(rows[1], "啊", "remaining Chinese codepoints should continue on the next row");
  }

  {
    expect_true(utf8AutoScrollOffset(0, 500) == 0, "no overflow should never scroll");
    expect_true(utf8AutoScrollOffset(3, 500, 800, 1200) == 0, "scroll should hold at the newest row first");
    expect_true(utf8AutoScrollOffset(3, 1200, 800, 1200) == 0, "scroll should still be at the newest row at hold boundary");
    expect_true(utf8AutoScrollOffset(3, 2000, 800, 1200) == 1, "scroll should advance after the hold interval");
    expect_true(utf8AutoScrollOffset(3, 5200, 800, 1200) == 0, "scroll should loop back to the newest row");
  }

  return 0;
}
