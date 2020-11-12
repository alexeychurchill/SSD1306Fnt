import argparse
import itertools
import freetype


debug_mode = False
ssd1306_page_size = 8


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
        width=None,
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

    glyph_appended = append_glyph(glyph_2d, width, height) if width is not None else append_height(glyph_2d, height)

    if debug_mode:
        if left_fields > 0 or right_fields > 0:
            print(f'Will add fields to the glyph: L: {left_fields} R: {right_fields}')

    result = glyph_insert_empty_cols(glyph_appended, columns_left=left_fields, columns_right=right_fields)

    if debug_mode:
        print('Ready glyph: ')
        print_image(result)

    return result


def convert_to_ssd1306_format(glyph_2d):
    glyph_h = len(glyph_2d)
    if glyph_h < 1:
        raise Exception('Glyph has incorrect height!')

    glyph_w = len(glyph_2d[0])
    if glyph_w < 1:
        raise Exception('Glyph has incorrect width!')

    if glyph_h % 8 != 0:
        raise Exception('Glyph must have height multiple of 8')

    glyph_rotated = [[glyph_2d[y][x] for y in range(glyph_h)] for x in range(glyph_w)]

    if debug_mode:
        print('Transformed glyph for the SSD1306: ')
        print_image(glyph_rotated)

    page_per_col = glyph_h // ssd1306_page_size

    if debug_mode:
        print(f'Glyph is {glyph_w} x {glyph_h} --> each glyph column will take {page_per_col} pages')

    def take_page(col, page):
        page_start = page * ssd1306_page_size
        page_end = page_start + ssd1306_page_size
        return glyph_rotated[col][page_start:page_end]

    glyph_paged = [[take_page(col, page) for page in range(page_per_col)] for col in range(glyph_w)]

    if debug_mode:
        print('Paged glyph:')
        for col in range(glyph_w):
            for page in range(page_per_col):
                print(f'Page {page}: |', end='')
                for row in range(ssd1306_page_size):
                    print('#' if glyph_paged[col][page][row] > 0 else '.', end='')
                print('| ', end='')
            print(end='\n')

    def get_pixel(page, y):
        return page[y] << y

    result = list()

    for col in range(glyph_w):
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

        ssd_glyph = convert_to_ssd1306_format(glyph)
        real_h = len(glyph)
        real_w = len(glyph[0])
        return [real_w, real_h] + ssd_glyph
    return [build_glyph(char) for char in chars]


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


def app():
    args = parse_args()
    global debug_mode
    debug_mode = args.debug
    face = freetype.Face(args.fontfile)

    glyph_w = args.glyph_width
    glyph_h = args.glyph_height

    if glyph_h < ssd1306_page_size:
        glyph_h = ssd1306_page_size
        print(f'WARNING! Glyph height can\'t be less than {ssd1306_page_size}! Was set to {glyph_h}')

    glyph_h_rem = glyph_h % ssd1306_page_size
    if glyph_h_rem > 0:
        glyph_h += ssd1306_page_size - glyph_h_rem
        print(f'WARNING! Glyph height wasn\'t multiple to {ssd1306_page_size}. Was set to {glyph_h}')

    ssd_data = prepare_for_ssd1306(face, ')', glyph_w, glyph_h, args.fields_left, args.fields_right)
    print(', '.join([f'0x{data:0>2X}' for data in ssd_data]))

    chars_to_gen = parse_chars_to_convert(args.chars)


    if debug_mode:
        print(f'Glyphs to generate: {len(chars_to_gen)}')


if __name__ == '__main__':
    # print(ord('ї'.encode('cp1251')))
    app()
