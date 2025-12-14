import re
import sys
import os
import unicodedata

import argparse
parser = argparse.ArgumentParser(description="对齐流程图中的竖线")
parser.add_argument("--input", "-i", type=str, default=r"C:\Users\wanglb\Desktop\new 11.txt",
                    help="输入文件路径（使用 '-' 或留空表示从标准输入读取）")
parser.add_argument("--output", "-o", type=str, default=None,
                    help="输出文件路径（默认: 输出到标准输出）")
parser.add_argument("--debug", action="store_true", help="显示调试信息")
args = parser.parse_args()

# 从文件或标准输入读取输入
if args.input is None or args.input == '-':
    # 从标准输入读取
    if args.debug:
        print("从标准输入读取...", file=sys.stderr)
    try:
        text_raw = sys.stdin.read()
    except Exception as e:
        print(f"错误: 无法从标准输入读取: {e}", file=sys.stderr)
        sys.exit(1)
else:
    # 从文件读取
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
def is_wide_char(char):
    """
    判断字符是否占两个字符位置（全角字符）
    包括：汉字、中文标点、全角字母数字符号等
    """
    # 使用 unicodedata 的 east_asian_width 属性判断
    # 'W' (Wide) 和 'F' (Fullwidth) 表示占两个位置
    width = unicodedata.east_asian_width(char)
    if width in ('W', 'F'):
        return True
    
    # 补充一些特殊情况：CJK符号和标点等
    code = ord(char)
    if (
        # CJK符号和标点
        (0x3000 <= code <= 0x303F) or
        # 平假名
        (0x3040 <= code <= 0x309F) or
        # 片假名
        (0x30A0 <= code <= 0x30FF) or
        # CJK统一汉字
        (0x4E00 <= code <= 0x9FFF) or
        # CJK扩展A
        (0x3400 <= code <= 0x4DBF) or
        # 全角字符块
        (0xFF00 <= code <= 0xFFEF)
    ):
        return True
    
    return False

def count_wide_chars(text):
    """
    计算文本中占两个字符位置的字符数量
    """
    return sum(1 for c in text if is_wide_char(c))

def has_text_and_pipe(line):
    """检查行是否含有文字和竖线"""
    has_text = bool(re.search(r'[^\s│┐┌└┘├┤┬┴╭╮╰╯]', line))  # 有非空白、非框线字符
    has_pipe = '│' in line
    return has_text and has_pipe

def find_all_pipes(line):
    """
    找到行中所有竖线的位置（考虑包括汉字在内的全角字符占2个字符位置）
    返回: [(字符索引, 显示位置), ...]
    """
    positions = []
    for i, char in enumerate(line):
        if char == '│':
            # 计算0到i之间占两个位置的字符数量
            amount_of_wide_chars = count_wide_chars(line[:i])
            # 实际显示位置 = 字符索引 + 前面全角字符的数量
            actual_pos = i + amount_of_wide_chars
            positions.append((i, actual_pos))  # (字符索引, 显示位置)
    return positions

def find_all_bottom_corners(line):
    """
    找到行中所有下角标字符"┘"的位置（考虑包括汉字在内的全角字符占2个字符位置）
    返回: [(字符索引, 显示位置), ...]
    """
    positions = []
    for i, char in enumerate(line):
        if char == '┘':
            # 计算0到i之间占两个位置的字符数量
            amount_of_wide_chars = count_wide_chars(line[:i])
            # 实际显示位置 = 字符索引 + 前面全角字符的数量
            actual_pos = i + amount_of_wide_chars
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
def find_nearest_corner(pipe_line_idx, pipe_display_col, lines, row_range=6, col_range=3, search_chars='┐┌'):
    """
    查找与竖线或下角标字符最近的角字符位置（考虑显示位置）
    pipe_display_col: 竖线或下角标字符的显示位置
    search_chars: 要查找的角字符，默认为'┐┌'（用于竖线），也可以是'┐┌'（用于┘）
    在上下行（row_range行内）和左右列（col_range列内）范围内查找最近的角字符
    返回: (target_display_col, distance, source, target_line_idx, target_char_idx)
    """
    best_pos = None
    best_distance = float('inf')
    best_source = None
    best_line_idx = None
    best_char_idx = None
    
    # 在Top line中查找
    for row_offset in range(1, row_range + 1):
        if pipe_line_idx - row_offset >= 0:
            check_line_idx = pipe_line_idx - row_offset
            check_line = lines[check_line_idx]
            # 查找该行中所有目标角字符，计算它们的显示位置
            for char_idx, char in enumerate(check_line):
                if char in search_chars:
                    # 计算该字符的显示位置
                    amount_of_wide_chars = count_wide_chars(check_line[:char_idx])
                    display_col = char_idx + amount_of_wide_chars
                    # 检查是否在范围内
                    col_diff = display_col - pipe_display_col
                    if abs(col_diff) <= col_range:
                        # 计算距离：优先考虑列距离，行距离作为次要因素
                        distance = abs(col_diff) + row_offset * 0.5
                        if distance < best_distance:
                            best_distance = distance
                            best_pos = display_col  # 返回显示位置
                            best_source = f'above_{row_offset}'
                            best_line_idx = check_line_idx
                            best_char_idx = char_idx
        
    if best_pos is not None:
        return best_pos, best_distance, best_source, best_line_idx, best_char_idx
    
    return None, None, None, None, None

def find_targets_for_all_lines(lines):
    """
    为所有含竖线的行找到目标位置
    返回: targets = {line_idx: [(char_idx, display_pos, target_col, distance, source), ...]}
    """
    # 重新查找所有含文字和竖线的行
    current_pipe_lines = []
    for idx, line in enumerate(lines):
        if has_text_and_pipe(line):
            pipe_positions = find_all_pipes(line)
            if pipe_positions:
                current_pipe_lines.append((idx, line, pipe_positions))
    
    # 为每个含竖线的行，为每个竖线找到目标位置
    targets = {}
    for line_idx, line, pipe_positions in current_pipe_lines:
        line_targets = []
        for char_idx, display_pos in pipe_positions:
            target_col, distance, source, target_line_idx, target_char_idx = find_nearest_corner(line_idx, display_pos, lines, search_chars='┐┌')
            if target_col is not None:
                line_targets.append((char_idx, display_pos, target_col, distance, source, target_line_idx, target_char_idx, '│'))
                if args.debug:
                    print(f"Line {line_idx+1}: │ at char_idx {char_idx} (display_col {display_pos}) -> target ┐/┌ at col {target_col} (from {source}, distance={distance})")
            else:
                if args.debug:
                    print(f"Line {line_idx+1}: │ at char_idx {char_idx} (display_col {display_pos}) -> no ┐/┌ found")
        if line_targets:
            targets[line_idx] = line_targets
    
    # 处理含下角标字符"┘"的行
    for idx, line in enumerate(lines):
        bottom_corner_positions = find_all_bottom_corners(line)
        if bottom_corner_positions:
            line_targets = []
            for char_idx, display_pos in bottom_corner_positions:
                # 为"┘"查找对应的"┐"或"┌"（通常在top_line中，向上查找）
                target_col, distance, source, target_line_idx, target_char_idx = find_nearest_corner(idx, display_pos, lines, row_range=10, col_range=3, search_chars='┐┌')
                if target_col is not None:
                    line_targets.append((char_idx, display_pos, target_col, distance, source, target_line_idx, target_char_idx, '┘'))
                    if args.debug:
                        print(f"Line {idx+1}: ┘ at char_idx {char_idx} (display_col {display_pos}) -> target ┐/┌ at col {target_col} (from {source}, distance={distance})")
                else:
                    if args.debug:
                        print(f"Line {idx+1}: ┘ at char_idx {char_idx} (display_pos {display_pos}) -> no ┐/┌ found")
            if line_targets:
                if idx not in targets:
                    targets[idx] = []
                targets[idx].extend(line_targets)
    
    return targets

# 初始查找目标位置
if args.debug:
    print("====== INITIAL TARGET FINDING ======")
targets = find_targets_for_all_lines(lines)

if args.debug:
    print()


# ---------------------------------------
# Step 3: 对齐所有含竖线的行
# ---------------------------------------
def find_paired_corner_in_bottom_line(lines, top_line_idx, corner_char, corner_idx, max_search_range=10):
    """
    在对应的 bottom_line 中查找配对的角字符
    top_line 中的 ┐ 配对 bottom_line 中的 ┘
    top_line 中的 ┌ 配对 bottom_line 中的 └
    返回: (bottom_line_idx, paired_corner_idx) 或 (None, None)
    """
    if corner_char == '┐':
        paired_char = '┘'
    elif corner_char == '┌':
        paired_char = '└'
    else:
        return None, None
    
    # 从 top_line 向下查找对应的 bottom_line（包含配对角字符的行）
    for offset in range(1, max_search_range + 1):
        bottom_line_idx = top_line_idx + offset
        if bottom_line_idx >= len(lines):
            break
        
        bottom_line = lines[bottom_line_idx]
        
        # 在 bottom_line 中查找配对的角字符
        # 应该在相同或相近的列位置查找
        for i, char in enumerate(bottom_line):
            if char == paired_char:
                # 计算显示位置，检查是否与 top_line 中的角字符位置对应
                amount_of_wide_chars = count_wide_chars(bottom_line[:i])
                bottom_display_col = i + amount_of_wide_chars
                
                # 计算 top_line 中角字符的显示位置
                top_line = lines[top_line_idx]
                top_amount_of_wide_chars = count_wide_chars(top_line[:corner_idx])
                top_display_col = corner_idx + top_amount_of_wide_chars
                
                # 如果显示位置相同或相近（允许1个字符的误差），认为是配对的
                if abs(bottom_display_col - top_display_col) <= 1:
                    return bottom_line_idx, i
    
    return None, None

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
        content_after_indent = before_pipe[leading_spaces:]
        
        # 计算竖线前紧邻的空格数量（从右向左查找）
        trailing_spaces = 0
        for char in reversed(content_after_indent):
            if char == ' ':
                trailing_spaces += 1
            else:
                break
        
        # 优先删除竖线前的空格
        if chars_to_remove <= trailing_spaces:
            # 有足够的空格可以删除
            spaces_to_keep = trailing_spaces - chars_to_remove
            # 保留行首缩进 + 内容（去掉末尾的空格）+ 保留的空格 + 竖线及之后的内容
            content_without_trailing = content_after_indent[:-trailing_spaces] if trailing_spaces > 0 else content_after_indent
            new_line = " " * leading_spaces + content_without_trailing + " " * spaces_to_keep + line[char_idx:]
            return new_line, display_diff
        else:
            # 竖线前的空格不够，无法通过删除空格对齐
            # 这种情况下，不调整该行，让下一轮迭代时重新查找目标位置
            # 返回原行和0偏移，表示未进行任何调整
            if args.debug:
                print(f"    Warning: Not enough spaces before pipe (need {chars_to_remove}, have {trailing_spaces}), skipping adjustment")
            return line, 0

def align_lines_one_round(lines, targets, round_num=1):
    """
    执行一轮对齐：处理每行第一个错位的竖线
    返回: (aligned_lines, has_changes)
    """
    if args.debug:
        print(f"\n====== ALIGNMENT ROUND {round_num} ======")
    
    aligned = []
    has_changes = False
    
    for idx, line in enumerate(lines):
        if idx not in targets:
            # 不含竖线或找不到目标，直接保留
            aligned.append(line)
            continue
        
        # 获取该行所有需要调整的字符信息（竖线"│"或下角标字符"┘"）
        # 按位置从左到右排序，只处理第一个（最左边）错位的字符
        line_targets = sorted(targets[idx], key=lambda x: x[0])  # 从左到右排序
        
        if args.debug:
            char_types = [target[7] if len(target) > 7 else '│' for target in line_targets]
            print(f"[Line {idx+1}] original: {repr(line)}")
            print(f"  Found {len(line_targets)} items ({', '.join(set(char_types))}), will find the first misaligned one")
        
        if not line_targets:
            aligned.append(line)
            continue
        
        # 找到第一个（最左边的）需要调整的字符（display_pos != target_col）
        first_misaligned = None
        for target in line_targets:
            if len(target) > 7:
                char_idx, display_pos, target_col, distance, source, target_line_idx, target_char_idx, char_type = target
            else:
                # 兼容旧格式（只有竖线）
                char_idx, display_pos, target_col, distance, source, target_line_idx, target_char_idx = target
                char_type = '│'
            if display_pos != target_col:
                first_misaligned = target
                break
        
        # 如果没有找到需要调整的字符，说明都已对齐，直接保留原行
        if first_misaligned is None:
            aligned.append(line)
            continue
        
        # 找到需要调整的字符，标记有变化
        has_changes = True
        
        if len(first_misaligned) > 7:
            char_idx, display_pos, target_col, distance, source, target_line_idx, target_char_idx, char_type = first_misaligned
        else:
            # 兼容旧格式
            char_idx, display_pos, target_col, distance, source, target_line_idx, target_char_idx = first_misaligned
            char_type = '│'
        
        # 计算需要调整的显示位置差值
        display_diff = target_col - display_pos
        
        if args.debug:
            print(f"  First misaligned {char_type} at char_idx {char_idx} (display_col {display_pos}) -> target ┐/┌ at col {target_col}")
            print(f"    needed delta: {display_diff}")
        
        # 调整第一个字符（竖线"│"或下角标字符"┘"），后续字符会因为这次调整而相应变化
        if char_type == '┘':
            # 对于"┘"字符，使用与竖线相同的调整逻辑
            current_line, offset = adjust_line_for_pipe(line, char_idx, display_diff)
        else:
            # 对于竖线"│"
            current_line, offset = adjust_line_for_pipe(line, char_idx, display_diff)
        
        # 检查行是否真的改变了
        if current_line == line and display_diff < 0:
            # 竖线偏右且没有足够的空格可删，尝试将目标位置右移
            # 在目标角字符所在的行插入空格
            if target_line_idx is not None and target_char_idx is not None:
                # 获取目标行的当前状态
                if target_line_idx < len(aligned):
                    target_line = aligned[target_line_idx]
                else:
                    target_line = lines[target_line_idx]
                
                spaces_to_insert = -display_diff  # 需要右移的距离
                
                # 检查 target_char_idx 是否在有效范围内
                if target_char_idx >= len(target_line):
                    if args.debug:
                        print(f"    Warning: target_char_idx {target_char_idx} out of range for line {target_line_idx+1} (length {len(target_line)}), skipping target adjustment")
                    has_changes = False
                    aligned.append(current_line)
                    continue
                
                target_corner_char = target_line[target_char_idx]
                
                # 在目标角字符前插入"─"
                new_target_line = target_line[:target_char_idx] + "─" * spaces_to_insert + target_line[target_char_idx:]
                
                # 在对应的 bottom_line 中查找配对的角字符（┐配对┘，┌配对└）
                # 使用当前 lines 或 aligned 的状态来查找
                # search_lines = aligned if target_line_idx < len(aligned) else lines
                search_lines = lines
                bottom_line_idx, paired_corner_idx = find_paired_corner_in_bottom_line(
                    search_lines, target_line_idx, target_corner_char, target_char_idx
                )
                
                if bottom_line_idx is not None and paired_corner_idx is not None:
                    # 找到配对的角字符，也需要在它前面插入相同数量的"─"
                    # 获取 bottom_line 的当前状态
                    if bottom_line_idx < len(aligned):
                        bottom_line = aligned[bottom_line_idx]
                    else:
                        bottom_line = lines[bottom_line_idx]
                    
                    # 在配对角字符前插入"─"
                    new_bottom_line = bottom_line[:paired_corner_idx] + "─" * spaces_to_insert + bottom_line[paired_corner_idx:]
                    
                    # 更新 bottom_line
                    if bottom_line_idx < len(aligned):
                        aligned[bottom_line_idx] = new_bottom_line
                    else:
                        lines[bottom_line_idx] = new_bottom_line
                    
                    if args.debug:
                        print(f"    Found paired corner '{bottom_line[paired_corner_idx]}' in bottom_line {bottom_line_idx+1} at position {paired_corner_idx}, also adjusted")
                
                if target_line_idx < len(aligned):
                    # 目标行已经处理过，直接更新 aligned
                    aligned[target_line_idx] = new_target_line
                else:
                    # 目标行还没有处理，更新 lines 以便后续处理时使用
                    lines[target_line_idx] = new_target_line
                
                if args.debug:
                    print(f"    Adjusted target corner position by inserting {spaces_to_insert} '─' characters")
                    print(f"    Target line {target_line_idx+1} updated: {repr(new_target_line)}")
            else:
                # 无法调整目标位置，跳过这一行
                if args.debug:
                    print(f"    Cannot adjust target position (target_line_idx={target_line_idx}), skipping this line")
                has_changes = False
        elif current_line == line:
            # 行没有改变，不标记为有变化
            has_changes = False
        
        if args.debug:
            print(f"  aligned: {repr(current_line)}\n")
        
        aligned.append(current_line)
    
    return aligned, has_changes

# ---------------------------------------
# Step 3: 迭代对齐所有含竖线的行
# ---------------------------------------
aligned = lines
max_iterations = 10  # 最大迭代次数，防止无限循环
iteration = 0
has_changes = True

while has_changes and iteration < max_iterations:
    iteration += 1
    
    # 基于当前对齐结果，重新查找目标位置
    if iteration > 1:
        if args.debug:
            print(f"\n====== RE-FINDING TARGETS (Round {iteration}) ======")
        targets = find_targets_for_all_lines(aligned)
        if args.debug:
            print()
    
    # 执行一轮对齐
    aligned, has_changes = align_lines_one_round(aligned, targets, iteration)
    
    if not has_changes:
        if args.debug:
            print(f"\n所有竖线已对齐，共执行 {iteration} 轮调整。")
        break

if iteration >= max_iterations and has_changes:
    if args.debug:
        print(f"\n警告: 达到最大迭代次数 {max_iterations}，可能仍有未对齐的竖线。")

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
