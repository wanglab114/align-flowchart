import re
import sys

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
args = parser.parse_args()

# text_raw = sys.stdin.read()
text_raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")    #强制用 utf-8 解码文件
lines = text_raw.splitlines()

if args.debug:
    print("====== RAW INPUT ======")
    print(text_raw)
    print("========================\n")


# ---------------------------------------
# Step 1: 查找所有含竖线行
# ---------------------------------------
info = []
for idx, line in enumerate(lines):
    m = re.match(r"(\s*)([│])", line)
    # print([hex(ord(c)) for c in line])
    if m:
        indent = len(m.group(1))
        info.append((idx, line, indent))

# 若无竖线，直接输出原文
if not info:
    if args.debug:
        print("No vertical lines detected, output original text.")
    print(text_raw, end="")
    sys.exit(0)

if args.debug:
    print("====== MATCHED LINES ======")
    for idx, line, indent in info:
        print(f"Line {idx+1:3d} | indent={indent:2d} | {repr(line)}")
    print("===========================\n")


# ---------------------------------------
# Step 2: 计算最大缩进列（对齐目标）
# ---------------------------------------
target = max(indent for _, _, indent in info)

if args.debug:
    print(f"TARGET INDENT COLUMN = {target}\n")


# ---------------------------------------
# Step 3: 对齐所有含竖线的行
# ---------------------------------------
aligned = []
for idx, line in enumerate(lines):

    m = re.match(r"(\s*)([│|])(.*)", line)
    if not m:
        aligned.append(line)
        continue

    cur_indent = len(m.group(1))
    symbol = m.group(2)
    rest = m.group(3)

    diff = target - cur_indent

    # debug 输出
    if args.debug:
        print(f"[Line {idx+1}] original: {repr(line)}")
        print(f"  current indent: {cur_indent}")
        print(f"  needed delta : {diff}")

    if diff > 0:
        # 不足则补空格
        new_line = " " * diff + line
    elif diff < 0:
        # 若超出，则向左裁剪
        new_line = line[-diff:]
    else:
        new_line = line

    if args.debug:
        print(f"  aligned: {repr(new_line)}\n")

    aligned.append(new_line)

# ---------------------------------------
# Step 4: 输出最终结果
# ---------------------------------------
result = "\n".join(aligned)

if args.debug:
    print("====== FINAL OUTPUT ======")
    print(result)
    print("==========================")

print(result)
