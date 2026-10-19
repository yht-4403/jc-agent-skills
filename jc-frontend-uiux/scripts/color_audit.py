#!/usr/bin/env python3
"""颜色显影工具：把「脏 / 虚 / 肉 / 糊 / 突兀」翻译成 WCAG 对比度与 OKLCH 数值。

用法：
  color_audit.py oklch    <#hex> [<#hex> ...]        # 每个颜色的 L/C/H
  color_audit.py contrast <#A> <#B> [<#C> <#D> ...]  # 相邻两两成对的对比度
  color_audit.py family   <基准#hex> <#hex> [...]    # 各颜色相对基准色的色相距与色度比

判定区间（029/030 调研）：
  虚 ≈ 线条对比 1.2–1.4 ｜ 肉/糊 ≈ 相邻面对比 <1.1 ｜ 文字 ≥4.5:1 ｜ 非文字控件 ≥3:1
  色相距为圆环距（≤180°）：>150° 近补色=突兀 ｜ 90–150° 离族=需语义职务 ｜ <90° 同族
  脏 ≈ 低明度(L<0.6) + 高色度(C>0.15) 的颜色用作大面积底色
"""
import math
import sys


def srgb_to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def parse_hex(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"无效颜色: {value}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rel_luminance(rgb):
    r, g, b = (srgb_to_linear(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = rel_luminance(a), rel_luminance(b)
    lo, hi = min(la, lb), max(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def oklch(rgb):
    r, g, b = (srgb_to_linear(x) for x in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def hue_delta(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def cmd_oklch(args):
    for raw in args:
        L, C, H = oklch(parse_hex(raw))
        flags = []
        if L < 0.6 and C > 0.15:
            flags.append("低明度+高色度(作大面积底色会显脏,小面积强调可用)")
        print(f"{raw:9s} L={L:.3f} C={C:.4f} H={H:6.1f}° {' '.join(flags)}")


def cmd_contrast(args):
    if len(args) % 2:
        sys.exit("contrast 需要成对的颜色")
    for i in range(0, len(args), 2):
        a, b = args[i], args[i + 1]
        ratio = contrast(parse_hex(a), parse_hex(b))
        if ratio < 1.1:
            verdict = "肉/糊(相邻面不分)"
        elif 1.2 <= ratio <= 1.4:
            verdict = "虚(线条发虚)"
        elif ratio < 3:
            verdict = "仅装饰可用"
        elif ratio < 4.5:
            verdict = "非文字控件可用"
        else:
            verdict = "文字可用"
        print(f"{a} vs {b}: {ratio:.2f}:1  {verdict}")


def cmd_family(args):
    if len(args) < 2:
        sys.exit("family 需要基准色 + 至少一个比较色")
    base_l, base_c, base_h = oklch(parse_hex(args[0]))
    print(f"基准 {args[0]}: L={base_l:.3f} C={base_c:.4f} H={base_h:.1f}°")
    for raw in args[1:]:
        L, C, H = oklch(parse_hex(raw))
        d = hue_delta(base_h, H)
        if d > 150 and C >= base_c:
            verdict = "突兀(近补色且色度不低于基准)"
        elif d > 90:
            verdict = "离族(需语义职务)"
        else:
            verdict = "同族"
        print(
            f"{raw:9s} H={H:6.1f}° C={C:.4f}  色相距(圆环)={d:5.1f}°  色度比={C / base_c if base_c else 0:.2f}x {verdict}"
        )


COMMANDS = {"oklch": cmd_oklch, "contrast": cmd_contrast, "family": cmd_family}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
