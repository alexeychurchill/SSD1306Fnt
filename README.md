# SSD1306Fnt
ssd1306fnt.py is a simple script for generation of the fonts in the most suitable 
format for the SSD1306 OLED display controller. It accepts a font file and produces 
C source code (.h with interface and .c with corresponding font data) files with an 
array of the font glyphs data and lookup-function, which resolves an index of the 
glyph in array by given **UTF-8** code of the character. The script allows choosing 
for which symbol ranges you want to generate glyphs (so, you won't get any unnecessary 
glyphs). Script works only with UTF-8 for now.

### Commands
```
ssd1306fnt.py fontfile -cn <prefix for sources, name of .h and .c files> -c <char sets> -gh <glyph height>
```
- `fontfile` - file of a desired font
- `--cname`/`-cn` - prefix/suffix of the font related things in the source files, name of generated .h and .c files
- `--out_dir`/`-dir` - output directory, omit if current
- `--glyph_width`/`-gw` - glyph width
- `--glyph_height`/`-gh` - glyph height (default - 8, equal to the SSD1306 page "height")
- `--glyph_width_equal`/`-gweq` - make glyphs equal by width
- `--fields_left`/`-fl` - width of left indent
- `--fields_right`/`-fr` - width of right indent
- `--chars`/`-c` - sets of chars. Format: `single char` or `start char`-`end char`. 
    Can be used with few single chars and char ranges mixed

### Data generation format
The script generates a bunch of arrays containing glyphs data and a table with pointers to 
these arrays. 
Each glyph (row) contains the following information: 
1. _0 Byte_ - **Width** of the glyph
2. _1 Byte_ - **Height** of the glyph
3. _(Width x Height) / 8_ bytes of a glyph data

Each data byte consists of **8 pixels** - one **SSD1306 page's row**. So, actually, 
script is intended for working with **vertical addressing mode** (refer to 
SSD1306 datasheet for more information, please) during writes of text glyphs data 
to the SSD1306.   

### Dependencies
- [freetype-py](https://pypi.org/project/freetype-py/)

### TODO

- [ ] _(Optional)_ Create an additional script for the setup (e.g., setup `venv` and 
fetch all dependencies)
