#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

inline bool utf8ContainsNonAscii(const char* text) {
  if (!text) return false;
  for (const unsigned char* p = (const unsigned char*)text; *p; ++p) {
    if (*p & 0x80) return true;
  }
  return false;
}

inline size_t utf8CodepointBytes(unsigned char lead) {
  if ((lead & 0x80) == 0x00) return 1;
  if ((lead & 0xE0) == 0xC0) return 2;
  if ((lead & 0xF0) == 0xE0) return 3;
  if ((lead & 0xF8) == 0xF0) return 4;
  return 1;
}

inline bool utf8HasContinuationBytes(const char* text, size_t bytes) {
  if (!text || bytes <= 1) return true;
  for (size_t i = 1; i < bytes; ++i) {
    unsigned char c = (unsigned char)text[i];
    if (c == 0 || (c & 0xC0) != 0x80) return false;
  }
  return true;
}

inline size_t utf8NextCodepointBytes(const char* text, size_t maxBytes) {
  if (!text || !*text || maxBytes == 0) return 0;
  size_t bytes = utf8CodepointBytes((unsigned char)text[0]);
  if (bytes > maxBytes) return 0;
  if (bytes == 1) return 1;
  return utf8HasContinuationBytes(text, bytes) ? bytes : 1;
}

inline uint8_t utf8CodepointCells(const char* text, size_t bytes) {
  if (!text || bytes == 0) return 0;
  return (((unsigned char)text[0]) & 0x80) ? 2 : 1;
}

inline size_t utf8SafePrefixBytes(const char* text, size_t maxBytes) {
  if (!text) return 0;
  size_t used = 0;
  while (text[used] && used < maxBytes) {
    size_t cp = utf8NextCodepointBytes(text + used, maxBytes - used);
    if (cp == 0 || used + cp > maxBytes) break;
    used += cp;
  }
  return used;
}

inline void utf8TrimIncompleteTail(char* text) {
  if (!text) return;
  size_t safe = utf8SafePrefixBytes(text, strlen(text));
  text[safe] = 0;
}

inline uint16_t utf8DisplayCells(const char* text, size_t maxBytes) {
  if (!text) return 0;
  size_t used = 0;
  uint16_t cells = 0;
  while (text[used] && used < maxBytes) {
    size_t cp = utf8NextCodepointBytes(text + used, maxBytes - used);
    if (cp == 0 || used + cp > maxBytes) break;
    cells += utf8CodepointCells(text + used, cp);
    used += cp;
  }
  return cells;
}

inline uint16_t utf8DisplayCells(const char* text) {
  if (!text) return 0;
  return utf8DisplayCells(text, strlen(text));
}

inline size_t utf8ClipDisplayBytes(const char* text, size_t textBytes, uint8_t maxCells, size_t maxBytes) {
  if (!text) return 0;
  size_t limit = textBytes < maxBytes ? textBytes : maxBytes;
  size_t used = 0;
  uint8_t cells = 0;
  while (text[used] && used < limit) {
    size_t cp = utf8NextCodepointBytes(text + used, limit - used);
    if (cp == 0 || used + cp > limit) break;
    uint8_t nextCells = utf8CodepointCells(text + used, cp);
    if ((uint16_t)cells + nextCells > maxCells) break;
    cells += nextCells;
    used += cp;
  }
  return used;
}

inline size_t utf8ClipDisplayBytes(const char* text, uint8_t maxCells, size_t maxBytes) {
  return utf8ClipDisplayBytes(text, text ? strlen(text) : 0, maxCells, maxBytes);
}

inline void utf8CopyTruncate(char* out, size_t outSize, const char* text) {
  if (!out || outSize == 0) return;
  if (!text) {
    out[0] = 0;
    return;
  }
  size_t bytes = utf8SafePrefixBytes(text, outSize - 1);
  memcpy(out, text, bytes);
  out[bytes] = 0;
}

template <size_t N>
inline void utf8CopyTruncate(char (&out)[N], const char* text) {
  utf8CopyTruncate(out, N, text);
}

inline uint8_t utf8AutoScrollOffset(
  uint8_t maxBack,
  uint32_t elapsedMs,
  uint16_t stepMs = 900,
  uint16_t holdMs = 1400
) {
  if (maxBack == 0 || stepMs == 0) return 0;
  if (elapsedMs <= holdMs) return 0;

  uint32_t shifted = elapsedMs - holdMs;
  uint32_t states = (uint32_t)maxBack + 2;
  uint32_t index = (shifted / stepMs) % states;
  return index > maxBack ? 0 : (uint8_t)index;
}

template <size_t ROW_BYTES>
uint8_t utf8WrapInto(const char* in, char (*out)[ROW_BYTES], uint8_t maxRows, uint8_t width, bool continuationIndent = true) {
  if (!out || maxRows == 0 || ROW_BYTES < 2 || width == 0) return 0;
  for (uint8_t i = 0; i < maxRows; ++i) out[i][0] = 0;
  if (!in || !*in) return 0;

  uint8_t row = 0;
  size_t colBytes = 0;
  uint8_t colCells = 0;

  auto beginRow = [&](bool continuation) {
    out[row][0] = 0;
    colBytes = 0;
    colCells = 0;
    if (continuation && continuationIndent && width > 1) {
      out[row][0] = ' ';
      out[row][1] = 0;
      colBytes = 1;
      colCells = 1;
    }
  };

  beginRow(false);

  const char* p = in;
  while (*p && row < maxRows) {
    while (*p == ' ') ++p;
    if (!*p) break;

    const char* word = p;
    while (*p && *p != ' ') ++p;
    size_t wordBytes = (size_t)(p - word);
    if (wordBytes == 0) continue;

    bool rowHasText = colBytes > 0 && !(continuationIndent && colBytes == 1 && out[row][0] == ' ');
    uint8_t prefixCells = rowHasText ? 1 : 0;
    uint16_t wordCells = utf8DisplayCells(word, wordBytes);
    if (colCells + prefixCells + wordCells > width && colBytes > 0) {
      out[row][colBytes] = 0;
      if (++row >= maxRows) return row;
      beginRow(true);
      rowHasText = false;
      prefixCells = 0;
    } else if (rowHasText) {
      uint8_t cellsAfterPrefix = (width > (uint8_t)(colCells + 1)) ? (uint8_t)(width - colCells - 1) : 0;
      size_t bytesAfterPrefix = (ROW_BYTES - 1 > colBytes + 1) ? (ROW_BYTES - 1 - colBytes - 1) : 0;
      if (cellsAfterPrefix == 0 || utf8ClipDisplayBytes(word, wordBytes, cellsAfterPrefix, bytesAfterPrefix) == 0) {
        out[row][colBytes] = 0;
        if (++row >= maxRows) return row;
        beginRow(true);
        rowHasText = false;
        prefixCells = 0;
      }
    }

    if (rowHasText) {
      if (colBytes + 1 >= ROW_BYTES) {
        out[row][colBytes] = 0;
        if (++row >= maxRows) return row;
        beginRow(true);
      } else {
        out[row][colBytes++] = ' ';
        out[row][colBytes] = 0;
        colCells += 1;
      }
    }

    const char* seg = word;
    size_t remainingBytes = wordBytes;
    while (remainingBytes > 0 && row < maxRows) {
      uint8_t remainingCells = (width > colCells) ? (width - colCells) : 0;
      size_t remainingRowBytes = (ROW_BYTES - 1 > colBytes) ? (ROW_BYTES - 1 - colBytes) : 0;
      size_t take = utf8ClipDisplayBytes(seg, remainingBytes, remainingCells, remainingRowBytes);
      if (take == 0 && remainingRowBytes > 0 && colBytes == 0) {
        take = utf8NextCodepointBytes(seg, remainingRowBytes);
      }
      if (take == 0) {
        out[row][colBytes] = 0;
        if (++row >= maxRows) return row;
        beginRow(true);
        continue;
      }

      memcpy(&out[row][colBytes], seg, take);
      colBytes += take;
      out[row][colBytes] = 0;
      colCells += (uint8_t)utf8DisplayCells(seg, take);
      seg += take;
      remainingBytes -= take;

      if (remainingBytes > 0) {
        if (++row >= maxRows) return row;
        beginRow(true);
      }
    }
  }

  if (colBytes > 0) return row + 1;
  return row;
}
