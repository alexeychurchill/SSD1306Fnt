import argparse
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
    args_parser.add_argument('--glyph_width', '-gw', type=int, default=5, help='glyph width (default - 5)')
    args_parser.add_argument(
        '--glyph_height', '-gh',
        type=int,
        default=8,
        help='glyph height (default - 8, equal to the SSD1306 page "height")'
    )
    args_parser.add_argument('--encoding', '-e', type=str, help='chars encoding')
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
    return [[0] * diff_start + glyph_row + [0] * diff_end for glyph_row in glyph_2d]


def append_glyph(glyph_2d, target_width, target_height):
    return append_height(append_width(glyph_2d, target_width), target_height)


def generate_glyph(face, character, width, height):
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

    glyph_ready = append_glyph(glyph_2d, width, height)

    if debug_mode:
        print('Ready glyph: ')
        print_image(glyph_ready)

    return glyph_ready


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
        return page[y] << (ssd1306_page_size - 1 - y)

    result = list()

    for col in range(glyph_w):
        for page in range(page_per_col):
            page_bin = [get_pixel(glyph_paged[col][page], row) for row in range(len(glyph_paged[col][page]))]
            page_value = 0x0
            for page_pixel in page_bin:
                page_value |= page_pixel
            result.append(page_value)

    return result


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

    glyph = generate_glyph(face, 'О', glyph_w, glyph_h)


if __name__ == '__main__':
    # print(ord('ї'.encode('cp1251')))
    app()
