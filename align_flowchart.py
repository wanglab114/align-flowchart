import re
import sys

text = sys.stdin.read().splitlines()

# 找出所有含竖线的行
line_info = []
for line in text:
    match = re.match(r"(\s*)([│|])", line)
    if match:
        line_info.append((line, len(match.group(1))))

if not line_info:
    print("\n".join(text))
    sys.exit(0)

# 计算最大缩进
target = max(indent for _, indent in line_info)

# 处理：把所有竖线前面的空白补齐
new_lines = []
for line in text:
    match = re.match(r"(\s*)([│|])(.*)", line)
    if match:
        cur_indent = len(match.group(1))
        change = target - cur_indent
        if change > 0:
            line = " " * change + line
        elif change < 0:
            line = line[-change:]
    new_lines.append(line)

print("\n".join(new_lines))
