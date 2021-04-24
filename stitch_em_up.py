from os.path import join
import argparse
import os
import re

# Third party
from PIL import Image, ImageDraw, ImageFont


# Stitch em up
parser = argparse.ArgumentParser(description='Stitch together GIS terrain images')
parser.add_argument('input_directory_path', metavar='source', type=str, help='Path of source directory containing images to be stitched')
parser.add_argument('output_file_path', metavar='destination', type=str, help='Path of destination image')
parser.add_argument('--bg-color', metavar=('r', 'g', 'b', 'a'), type=int, nargs=4, default=(0, 0, 0, 0), help='Background color of destination image (each component in range [0, 255])')
parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
args = parser.parse_args()


def stitch_tile(source_dir, tile, verbose):
    tmp_path = tile[list(tile)[0]]
    tmp_file = Image.open(join(source_dir, tmp_path))
    blank_image = Image.new('RGBA', tmp_file.size, (0, 0, 0, 0))

    quad_image_nw = Image.open(join(source_dir, tile['nw'])) if 'nw' in tile else blank_image
    quad_image_ne = Image.open(join(source_dir, tile['ne'])) if 'ne' in tile else blank_image
    quad_image_se = Image.open(join(source_dir, tile['se'])) if 'se' in tile else blank_image
    quad_image_sw = Image.open(join(source_dir, tile['sw'])) if 'sw' in tile else blank_image

    if (quad_image_nw.size != quad_image_ne.size or quad_image_ne.size != quad_image_se.size or quad_image_se.size != quad_image_sw.size) and verbose:
        print('Size mismatch')

    image_width = max(quad_image_nw.width + quad_image_ne.width, quad_image_sw.width + quad_image_se.width, quad_image_nw.width + quad_image_se.width, quad_image_sw.width + quad_image_ne.width)
    image_height = max(quad_image_nw.height + quad_image_sw.height, quad_image_ne.height + quad_image_se.height, quad_image_nw.height + quad_image_se.height, quad_image_sw.height + quad_image_ne.height)
    tile_image = Image.new('RGBA', (image_width, image_height), (255, 255, 0, 255))

    # This is intentional
    tile_image.paste(quad_image_ne, (tile_image.width - quad_image_ne.width,                                        0))
    tile_image.paste(quad_image_se, (tile_image.width - quad_image_se.width, tile_image.height - quad_image_se.height))
    tile_image.paste(quad_image_sw, (                                     0, tile_image.height - quad_image_sw.height))

    tile_image.paste(quad_image_nw, (               0,                 0))
    tile_image.paste(quad_image_ne, (image_width // 2,                 0))
    tile_image.paste(quad_image_se, (image_width // 2, image_height // 2))
    tile_image.paste(quad_image_sw, (               0, image_height // 2))

    return tile_image


def main(source_dir, out_file, bg_color, verbose):
    filename_expr = re.compile(r'm_(\d+)_(\w+)_(\d+)_(\w+)_(\d+)_(\d+).png')
    location_expr = re.compile(r'(\d{2})(\d{3})(\d+)')
    tiles = {}
    completed_tiles = {}
    tile_coords = {}

    for file in os.listdir(source_dir):
        if match := filename_expr.match(file):
            idx = match.group(1)
            quad = match.group(2)

            if idx in tiles:
                tiles[idx][quad] = file
            else:
                tiles[idx] = { quad: file }

    # One quadrangle is 8x8 tiles
    # See https://www.nrcs.usda.gov/Internet/FSE_DOCUMENTS/nrcs141p2_015644.pdf

    for tile_idx in tiles:
        if verbose:
            print(f'Processing tile {tile_idx}')
        
        tile = tiles[tile_idx]
        match = location_expr.match(tile_idx)
        latitude = int(match.group(1))
        longitude = int(match.group(2))
        quadrangle = int(match.group(3)) - 1

        tile_coords[tile_idx] = (
            8 * (180 - longitude) + (quadrangle % 8),
            8 * (90 - latitude) + (quadrangle // 8)
        )
        
        new_tile = stitch_tile(source_dir, tile, verbose)

        font = ImageFont.truetype('./Roboto-Regular.ttf', size=40)
        draw = ImageDraw.Draw(new_tile)
        draw.text((new_tile.width // 2, new_tile.height // 2), '+', font=font, fill='red', anchor='mm')

        completed_tiles[tile_idx] = new_tile
    
    coords = tile_coords.values()
    min_x = min(coords, key=lambda x: x[0])[0]
    max_x = max(coords, key=lambda x: x[0])[0]
    min_y = min(coords, key=lambda x: x[1])[1]
    max_y = max(coords, key=lambda x: x[1])[1]

    tile_count_width = max_x - min_x
    tile_count_height = max_y - min_y

    first_tile = completed_tiles[list(completed_tiles)[0]]
    tile_width = first_tile.width
    tile_height = first_tile.height

    image_width = tile_width * tile_count_width
    image_height = tile_height * tile_count_height

    final_image = Image.new('RGBA', (image_width, image_height), bg_color)

    for tile_idx in tile_coords:
        coords = tile_coords[tile_idx]
        new_coords = (coords[0] - min_x, coords[1] - min_y)
        tile = completed_tiles[tile_idx]
        final_image.paste(tile, (new_coords[0] * tile_width, new_coords[1] * tile_height))
    
    final_image.show()
    final_image.save(out_file)


if __name__ == '__main__':
    main(args.input_directory_path, args.output_file_path, tuple(args.bg_color), args.verbose)
