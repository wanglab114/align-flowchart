import re
import sys
import os

import argparse
parser = argparse.ArgumentParser(description="对齐流程图中的竖线")
parser.add_argument("--input", "-i", type=str, default=r"C:\Users\wanglb\Desktop\new 10.txt",
                    help="输入文件路径（默认: C:\\Users\\wanglb\\Desktop\\new 10.txt）")
parser.add_argument("--output", "-o", type=str, default=None,
                    help="输出文件路径（默认: 输出到标准输出）")
parser.add_argument("--debug", action="store_true", help="显示调试信息")
args = parser.parse_args()

# 从文件读取输入
input_file = args.input
if not os.path.exists(input_file):
    print(f"错误: 文件不存在: {input_file}", file=sys.stderr)
    sys.exit(1)

try:
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        text_raw = f.read()
except Exception as e:
    print(f"错误: 无法读取文件 {input_file}: {e}", file=sys.stderr)
    sys.exit(1)

lines = text_raw.splitlines()

if args.debug:
    print("====== RAW INPUT ======")
    print(text_raw)
    print("========================\n")


# ---------------------------------------
# Step 1: 查找所有含文字和竖线的行，记录所有竖线的位置
# ---------------------------------------
def has_text_and_pipe(line):
    """检查行是否含有文字和竖线"""
    has_text = bool(re.search(r'[^\s│┐┌└┘├┤┬┴╭╮╰╯]', line))  # 有非空白、非框线字符
    has_pipe = '│' in line
    return has_text and has_pipe

def find_all_pipes(line):
    """
    找到行中所有竖线的位置（考虑汉字占2个字符位置）
    返回: [(字符索引, 显示位置), ...]
    """
    positions = []
    for i, char in enumerate(line):
        if char == '│':
            # 计算0到i之间的汉字数量
            amount_of_chinese = sum(1 for c in line[:i] if '\u4e00' <= c <= '\u9fff')
            # 实际显示位置 = 字符索引 - 前面汉字的数量
            actual_pos = i + amount_of_chinese
            positions.append((i, actual_pos))  # (字符索引, 显示位置)
    return positions

pipe_lines = []  # (line_idx, line, pipe_positions[]) where pipe_positions is [(char_idx, display_pos), ...]
for idx, line in enumerate(lines):
    if has_text_and_pipe(line):
        pipe_positions = find_all_pipes(line)
        if pipe_positions:
            pipe_lines.append((idx, line, pipe_positions))

# 若无匹配行，直接输出原文
if not pipe_lines:
    if args.debug:
        print("No lines with text and vertical line detected, output original text.")
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(text_raw)
            if args.debug:
                print(f"结果已保存到: {args.output}")
        except Exception as e:
            print(f"错误: 无法写入文件 {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(text_raw, end="")
    sys.exit(0)

if args.debug:
    print("====== MATCHED LINES (text + │) ======")
    for idx, line, pipe_positions in pipe_lines:
        display_positions = [display_pos for _, display_pos in pipe_positions]
        print(f"Line {idx+1:3d} | display_columns={display_positions} | {repr(line)}")
    print("=====================================\n")


# ---------------------------------------
# Step 2: 为每个含竖线的行找到最近的┐或┌位置
# ---------------------------------------
def find_nearest_corner(pipe_line_idx, pipe_display_col, lines, row_range=2, col_range=2):
    """
    查找与竖线最近的┐或┌的位置（考虑显示位置）
    pipe_display_col: 竖线的显示位置
    在上下行（row_range行内）和左右列（col_range列内）范围内查找最近的┐或┌
    """
    best_pos = None
    best_distance = float('inf')
    best_source = None
    
    # 在上下行查找
    for row_offset in range(1, row_range + 1):
        # 检查上行
        if pipe_line_idx - row_offset >= 0:
            check_line = lines[pipe_line_idx - row_offset]
            # 查找该行中所有┐或┌，计算它们的显示位置
            for char_idx, char in enumerate(check_line):
                if char in '┐┌':
                    # 计算该字符的显示位置
                    amount_of_chinese = sum(1 for c in check_line[:char_idx] if '\u4e00' <= c <= '\u9fff')
                    display_col = char_idx - amount_of_chinese
                    # 检查是否在范围内
                    col_diff = display_col - pipe_display_col
                    if abs(col_diff) <= col_range:
                        # 计算距离：优先考虑列距离，行距离作为次要因素
                        distance = abs(col_diff) + row_offset * 0.5
                        if distance < best_distance:
                            best_distance = distance
                            best_pos = display_col  # 返回显示位置
                            best_source = f'above_{row_offset}'
        
        # 检查下行
        if pipe_line_idx + row_offset < len(lines):
            check_line = lines[pipe_line_idx + row_offset]
            # 查找该行中所有┐或┌，计算它们的显示位置
            for char_idx, char in enumerate(check_line):
                if char in '┐┌':
                    # 计算该字符的显示位置
                    amount_of_chinese = sum(1 for c in check_line[:char_idx] if '\u4e00' <= c <= '\u9fff')
                    display_col = char_idx - amount_of_chinese
                    # 检查是否在范围内
                    col_diff = display_col - pipe_display_col
                    if abs(col_diff) <= col_range:
                        # 计算距离：优先考虑列距离
                        distance = abs(col_diff) + row_offset * 0.5
                        if distance < best_distance:
                            best_distance = distance
                            best_pos = display_col  # 返回显示位置
                            best_source = f'below_{row_offset}'
    
    if best_pos is not None:
        return best_pos, best_distance, best_source
    
    return None, None, None

# 为每个含竖线的行，为每个竖线找到目标位置
# targets: {line_idx: [(char_idx, display_pos, target_col, distance, source), ...]}
targets = {}
for line_idx, line, pipe_positions in pipe_lines:
    line_targets = []
    for char_idx, display_pos in pipe_positions:
        target_col, distance, source = find_nearest_corner(line_idx, display_pos, lines)
        if target_col is not None:
            line_targets.append((char_idx, display_pos, target_col, distance, source))
            if args.debug:
                print(f"Line {line_idx+1}: │ at char_idx {char_idx} (display_col {display_pos}) -> target ┐/┌ at col {target_col} (from {source}, distance={distance})")
        else:
            if args.debug:
                print(f"Line {line_idx+1}: │ at char_idx {char_idx} (display_col {display_pos}) -> no ┐/┌ found")
    if line_targets:
        targets[line_idx] = line_targets

if args.debug:
    print()


# ---------------------------------------
# Step 3: 对齐所有含竖线的行
# ---------------------------------------
def adjust_line_for_pipe(line, char_idx, display_diff):
    """
    调整一行中的单个竖线位置
    char_idx: 竖线的字符索引
    display_diff: 显示位置的差值（目标显示位置 - 当前显示位置）
    返回调整后的行和位置偏移量（用于后续竖线的位置调整）
    """
    if display_diff == 0:
        # 已经对齐，无需调整
        return line, 0
    elif display_diff > 0:
        # 竖线位置偏左，需要在竖线前插入空格
        # display_diff 是显示位置的差值，直接作为插入的空格数
        new_line = line[:char_idx] + " " * display_diff + line[char_idx:]
        return new_line, display_diff
    else:
        # 竖线位置偏右，需要删除竖线前的字符
        chars_to_remove = -display_diff
        before_pipe = line[:char_idx]
        
        # 保留行首的连续空格（缩进）
        leading_spaces = len(before_pipe) - len(before_pipe.lstrip())
        non_space_part = before_pipe[leading_spaces:]
        
        # 优先删除非空格字符，如果不够再删除空格
        if chars_to_remove <= len(non_space_part):
            # 只删除非空格字符（从右向左）
            new_non_space = non_space_part[:-chars_to_remove] if chars_to_remove < len(non_space_part) else ""
            new_line = " " * leading_spaces + new_non_space + line[char_idx:]
        else:
            # 需要删除所有非空格字符和部分空格
            remaining = chars_to_remove - len(non_space_part)
            new_spaces = max(0, leading_spaces - remaining)
            new_line = " " * new_spaces + line[char_idx:]
        
        return new_line, display_diff  # display_diff是负数，表示向左移动

aligned = []
for idx, line in enumerate(lines):
    if idx not in targets:
        # 不含竖线或找不到目标，直接保留
        aligned.append(line)
        continue
    
    # 获取该行所有需要调整的竖线信息
    # 按位置从左到右排序，只处理第一个（最左边）错位的竖线
    line_targets = sorted(targets[idx], key=lambda x: x[0])  # 从左到右排序
    
    if args.debug:
        print(f"[Line {idx+1}] original: {repr(line)}")
        print(f"  Found {len(line_targets)} pipes, will find the first misaligned one")
    
    if not line_targets:
        aligned.append(line)
        continue
    
    # 找到第一个（最左边的）需要调整的竖线（display_pos != target_col）
    first_misaligned = None
    for target in line_targets:
        char_idx, display_pos, target_col, distance, source = target
        if display_pos != target_col:
            first_misaligned = target
            break
    
    # 如果没有找到需要调整的竖线，说明都已对齐，直接保留原行
    if first_misaligned is None:
        aligned.append(line)
        continue
    
    char_idx, display_pos, target_col, distance, source = first_misaligned
    
    # 计算需要调整的显示位置差值
    display_diff = target_col - display_pos
    
    if args.debug:
        print(f"  First pipe at char_idx {char_idx} (display_col {display_pos}) -> target ┐/┌ at col {target_col}")
        print(f"    needed delta: {display_diff}")
    
    # 只调整第一个竖线，后续竖线会因为这次调整而相应变化
    current_line, offset = adjust_line_for_pipe(line, char_idx, display_diff)
    
    if args.debug:
        print(f"  aligned: {repr(current_line)}\n")
    
    aligned.append(current_line)

# ---------------------------------------
# Step 4: 输出最终结果
# ---------------------------------------
result = "\n".join(aligned)

if args.debug:
    print("====== FINAL OUTPUT ======")
    print(result)
    print("==========================")

# 输出结果
if args.output:
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        if args.debug:
            print(f"\n结果已保存到: {args.output}")
    except Exception as e:
        print(f"错误: 无法写入文件 {args.output}: {e}", file=sys.stderr)
        sys.exit(1)
else:
    print(result)
