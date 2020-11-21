import argparse
import itertools
import freetype


debug_mode = False
ssd1306_page_size = 8
c_glyph_line_max_items = 8
c_lookup_func_arg_name = 'utf8_code'
c_disclaimer = """/**
 * 
 * ******************** DO NOT MODIFY THIS FILE MANUALLY! ********************
 * The file was generated with SSD1306Fnt font generator, so do not edit it  
 * unless you are 100000% sure in your actions. If you need something to have 
 * changed in the file, the best solution is to use SSD1306Fnt again. 
 *
 **/
"""


def parse_args():
    args_parser = argparse.ArgumentParser(description='Font faces converter for the SSD1306 displays.\nConverts font '
                                                      'files to the C headers (.h) which are easily compatible with '
                                                      'SSD1306 frame buffer.')

    args_parser.add_argument('fontfile', type=argparse.FileType('rb'), help='file of a desired font')
    args_parser.add_argument(
        'out',
        type=argparse.FileType('w', encoding='UTF-8'),
        help='output file (usually, file with .h extension)'
    )
    args_parser.add_argument(
        '--cname',
        '-cn',
        type=str,
        required=True,
        help='prefix/suffix of the font related things in the .h out file'
    )
    args_parser.add_argument('--glyph_width', '-gw', type=int, help='glyph width')
    args_parser.add_argument(
        '--glyph_height', '-gh',
        type=int,
        default=8,
        required=True,
        help='glyph height (default - 8, equal to the SSD1306 page "height")'
    )
    args_parser.add_argument('--fields_left', '-fl', type=int, default=0, help='width of left indent')
    args_parser.add_argument('--fields_right', '-fr', type=int, default=0, help='width of right indent')
    args_parser.add_argument('--chars', '-c', nargs='*', help='sets of chars')
    args_parser.add_argument('--debug', '-dbg', help='print some debug info', action='store_true', default=False)
    return args_parser.parse_args()


def print_image(img_2d, off='.', on='#'):
    for row in img_2d:
        for pixel in row:
            print(on if pixel > 0 else off, end='')
        print(end='\n')


def binarize(glyph, threshold=1):
    return [1 if pixel >= threshold else 0 for pixel in glyph]


def image_to_2d(linear_img, w, h):
    return [linear_img[(y * w):(y * w + w)] for y in range(0, h)]


def glyph_insert_empty_cols(glyph_2d, columns_left=0, columns_right=0):
    return [[0] * columns_left + glyph_row + [0] * columns_right for glyph_row in glyph_2d]


def append_height(glyph_2d, target_height):
    if len(glyph_2d) < 1:
        raise Exception("Glyph is empty!")

    count_to_append = target_height - len(glyph_2d)
    width = len(glyph_2d[0])
    appendix = [[0] * width for _ in range(count_to_append)]
    return appendix + glyph_2d


def append_width(glyph_2d, target_width):
    if len(glyph_2d) < 1:
        raise Exception("Glyph is empty!")

    glp_width = len(glyph_2d[0])
    if glp_width < 1:
        raise Exception("Glyph has no width!")

    width_diff = target_width - glp_width
    if width_diff < 0:
        raise Exception("Glyph has bigger width than it should be appended!")

    if width_diff == 0:
        return glyph_2d

    diff_start = width_diff // 2
    diff_end = width_diff - diff_start  # For cases, when width_diff cannot be divided by 2 w/o reminder
    return glyph_insert_empty_cols(glyph_2d, diff_start, diff_end)


def append_glyph(glyph_2d, target_width, target_height):
    return append_height(append_width(glyph_2d, target_width), target_height)


def generate_glyph(
        face,
        character,
        width=0,
        height=ssd1306_page_size,
        left_fields=0,
        right_fields=0
):
    if debug_mode:
        print('--------------------------------------')
        print(f'Generating char glyph for {character}, desired size: {width} x {height}...')

    face.set_pixel_sizes(width, height)
    face.load_char(character)
    glyph_bitmap = face.glyph.bitmap
    glyph_width = glyph_bitmap.width
    glyph_height = glyph_bitmap.rows

    if debug_mode:
        print(f'Real glyph size is {glyph_width} x {glyph_height}')

    glyph_img = glyph_bitmap.buffer
    glyph_binary = binarize(glyph_img)
    glyph_2d = image_to_2d(glyph_binary, glyph_width, glyph_height)

    if debug_mode:
        print('Generated glyph: ')
        print_image(glyph_2d)

    if debug_mode:
        if width is not None:
            print('Will append both horizontally and vertically')
        else:
            print('Will append only vertically')

    glyph_appended = append_glyph(glyph_2d, width, height) if width > 0 else append_height(glyph_2d, height)

    if debug_mode:
        if left_fields > 0 or right_fields > 0:
            print(f'Will add fields to the glyph: L: {left_fields} R: {right_fields}')

    result = glyph_insert_empty_cols(glyph_appended, columns_left=left_fields, columns_right=right_fields)

    if debug_mode:
        print('Ready glyph: ')
        print_image(result)

    return result


def glyph_size(glyph_2d):
    glyph_h = len(glyph_2d)
    if glyph_h < 1:
        raise Exception('Glyph has incorrect height!')

    glyph_w = len(glyph_2d[0])
    if glyph_w < 1:
        raise Exception('Glyph has incorrect width!')

    return glyph_w, glyph_h


def convert_to_ssd1306_format(glyph_2d, g_width, g_height):
    glyph_rotated = [[glyph_2d[y][x] for y in range(g_height)] for x in range(g_width)]

    if debug_mode:
        print('Transformed glyph for the SSD1306: ')
        print_image(glyph_rotated)

    page_per_col = g_height // ssd1306_page_size

    if debug_mode:
        print(f'Glyph is {g_width} x {g_height} --> each glyph column will take {page_per_col} pages')

    def take_page(col, page):
        page_start = page * ssd1306_page_size
        page_end = page_start + ssd1306_page_size
        return glyph_rotated[col][page_start:page_end]

    glyph_paged = [[take_page(col, page) for page in range(page_per_col)] for col in range(g_width)]

    if debug_mode:
        print('Paged glyph:')
        for col in range(g_width):
            for page in range(page_per_col):
                print(f'Page {page}: |', end='')
                for row in range(ssd1306_page_size):
                    print('#' if glyph_paged[col][page][row] > 0 else '.', end='')
                print('| ', end='')
            print(end='\n')

    def get_pixel(page, y):
        return page[y] << y

    result = list()

    for col in range(g_width):
        for page in range(page_per_col):
            page_bin = [get_pixel(glyph_paged[col][page], row) for row in range(len(glyph_paged[col][page]))]
            page_value = 0x0
            for page_pixel in page_bin:
                page_value |= page_pixel
            result.append(page_value)

    return result


def prepare_for_ssd1306(face, chars, glyph_w=None, glyph_h=0, left_fields=0, right_fields=0):
    def build_glyph(char):
        glyph = generate_glyph(
            face,
            char,
            width=glyph_w, height=glyph_h,
            left_fields=left_fields, right_fields=right_fields
        ) if glyph_w is not None else generate_glyph(
            face,
            char,
            height=glyph_h,
            left_fields=left_fields, right_fields=right_fields
        )

        real_w, real_h = glyph_size(glyph)

        if glyph_w is not None and real_w > glyph_w:
            print(f'WARNING! {char} ({utf_8_encode(char)}) exceeded width ({real_w}), cutting to {glyph_w}')
            real_w = glyph_w

        if 0 < glyph_h < real_h:
            print(f'WARNING! {char} ({utf_8_encode(char)}) exceeded height ({real_h}), cutting to {glyph_h}')
            real_h = glyph_h

        ssd_glyph = convert_to_ssd1306_format(glyph, real_w, real_h)

        return [real_w, real_h] + ssd_glyph
    return [(char, build_glyph(char)) for char in chars]


def parse_chars_to_convert(char_list):
    result = []
    for char_item in char_list:
        if len(char_item) > 1:  # We got a char range as an item
            (start, end) = char_item.split(sep='-')
            char_range = [chr(char) for char in range(ord(start), ord(end))] + [end]
            result += char_range
        else:
            result.append(char_item)
    result.sort()
    return result


def utf_8_encode(char):
    utf_8_code = char.encode('utf-8')
    return int.from_bytes(utf_8_code, byteorder='big')


def group_chars(chars):
    def calculate_offset(index):
        offset = utf_8_encode(chars[index]) - index
        return chars[index], offset

    chars_offset = [calculate_offset(index) for index in range(len(chars))]

    chars_grouped = itertools.groupby(chars_offset, lambda x: x[1])
    result = [(group_n, [char[0] for char in chars_group]) for (group_n, chars_group) in chars_grouped]

    if debug_mode:
        print('Grouped chars: ')
        for group in result:
            print(group)

    return result


def groups_reduce(groups):
    def reduce_group(group):
        (offset, items) = group
        item_min = min(items)
        item_max = max(items)
        return offset, item_min, item_max
    return [reduce_group(group) for group in groups]


def c_gen_group_if(group, arg_name):
    (offset, item_min, item_max) = group
    item_min = utf_8_encode(item_min)
    item_max = utf_8_encode(item_max)

    if item_min == item_max:
        return f'if ({item_min} == {arg_name}) ' \
               + '{ ' + f'return {arg_name} - {offset};' \
               + ' };'
    else:
        return f'if ({item_min} <= {arg_name} && {arg_name} <= {item_max}) ' \
               + '{ ' + f'return {arg_name} - {offset};' \
               + ' };'


def c_format_to_hex(value):
    return f'0x{value:0>2X}u'


def c_incl_guard(cname):
    return f'SSD1306_FONT_{cname.upper()}_H'


def c_write_header(fout, cname):
    incl_guard = c_incl_guard(cname)
    fout.write(f'#ifndef {incl_guard} // Start of {incl_guard}\n')
    fout.write(f'#define {incl_guard}\n\n')
    fout.write('#include <stdint.h>\n')


def c_write_glyph_count(fout, cname, count):
    fout.write(f'#define SSD1306_{cname.upper()}_GLYPH_COUNT\t0x{count:0>2X}u\n\n')


def c_gen_glyph_array_name(cname, char):
    return f'ssd1306_{cname.lower()}_glyph_data_{utf_8_encode(char)}'


def c_gen_glyph_data(cname, glyph):
    (char, data) = glyph
    max_items = c_glyph_line_max_items
    chunk_count = len(data) // max_items + (1 if len(data) % max_items > 0 else 0)
    chunks = [data[(chunk_ind * max_items):(chunk_ind * max_items) + max_items] for chunk_ind in range(0, chunk_count)]
    chunks_formatted = [', '.join([c_format_to_hex(c) for c in chunk]) for chunk in chunks]
    data_str = ', \n'.join(['\t' + item for item in chunks_formatted])
    return f'const uint8_t {c_gen_glyph_array_name(cname, char)}[] = ' + '{\n' + data_str + '\n};'


def c_write_glyphs_array(fout, cname, glyphs):
    c_glyphs_data = '\n\n'.join([c_gen_glyph_data(cname, glyph) for glyph in glyphs])
    glyphs_table = [c_gen_glyph_array_name(cname, glyph[0]) for glyph in glyphs]
    c_glyphs_table = f'const uint8_t(*ssd1306_{cname.lower()}_glyph_table)[] = ' + '{\n' + \
                     ', \n'.join(['\t' + glyph_ptr_name for glyph_ptr_name in glyphs_table]) + \
                     '\n};'

    fout.write(c_glyphs_data)
    fout.write('\n\n')
    fout.write(c_glyphs_table)
    fout.write('\n')


def c_write_lookup_func(fout, cname, reduced_groups):
    fout.write(f'uint32_t ssd1306_{cname.lower()}_get_glyph_index')
    fout.write(f'(uint32_t {c_lookup_func_arg_name})')
    fout.write(' {\n')

    for group in reduced_groups:
        c_group_code = c_gen_group_if(group, c_lookup_func_arg_name)
        fout.write('\t')
        fout.write(c_group_code)
        fout.write('\n')

    fout.write('\treturn 0;\n}\n')
    pass


def c_write_footer(fout, cname):
    guard = c_incl_guard(cname)
    fout.write(f'#endif // End of {guard}\n')


def app():
    args = parse_args()
    global debug_mode
    debug_mode = args.debug
    face = freetype.Face(args.fontfile)

    out_file = args.out
    cname = args.cname

    glyph_w = args.glyph_width
    glyph_h = args.glyph_height

    if glyph_h < ssd1306_page_size:
        glyph_h = ssd1306_page_size
        print(f'WARNING! Glyph height can\'t be less than {ssd1306_page_size}! Was set to {glyph_h}')

    glyph_h_rem = glyph_h % ssd1306_page_size
    if glyph_h_rem > 0:
        glyph_h += ssd1306_page_size - glyph_h_rem
        print(f'WARNING! Glyph height wasn\'t multiple to {ssd1306_page_size}. Was set to {glyph_h}')

    chars_to_gen = parse_chars_to_convert(args.chars)

    if debug_mode:
        print(f'Glyphs to generate: {len(chars_to_gen)}')

    ssd1306_glyph_data = prepare_for_ssd1306(face, chars_to_gen, glyph_w, glyph_h, args.fields_left, args.fields_right)
    reduced_char_groups = groups_reduce(group_chars(chars_to_gen))

    print(f'Done! Glyphs data took {len(ssd1306_glyph_data) * len(ssd1306_glyph_data[0])} bytes.\nWriting .h-file...')

    c_write_header(out_file, cname)
    out_file.write('\n')
    out_file.write(c_disclaimer)
    out_file.write('\n')
    c_write_glyph_count(out_file, cname, len(ssd1306_glyph_data))
    c_write_glyphs_array(out_file, cname, ssd1306_glyph_data)
    out_file.write('\n')
    c_write_lookup_func(out_file, cname, reduced_char_groups)
    out_file.write('\n')
    c_write_footer(out_file, cname)


if __name__ == '__main__':
    app()
