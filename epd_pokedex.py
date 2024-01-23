import argparse
import json
import logging
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps
from random import choice
from typing import Optional

'''
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pokemon_path = os.path.join(SCRIPTS_DIR, 'Pokemon')
epd_path = os.path.join(SCRIPTS_DIR, 'epd')
sys.path.append(os.path.dirname(pokemon_path))
sys.path.append(os.path.dirname(epd_path))
'''

script_path = os.path.dirname(os.path.realpath(__file__))
pokemon_list_file_name = 'pokemon.json'
pokemon_list_dir = os.path.join(script_path, 'pokemon')
pokemon_list_path = os.path.join(pokemon_list_dir, pokemon_list_file_name)
dex_dir_path = os.path.join(pokemon_list_dir, 'dex')
sprites_dir_path = os.path.join(pokemon_list_dir, 'sprites')
pokemon_sprites_path = os.path.join(sprites_dir_path, 'pokemon')
types_sprites_path = os.path.join(sprites_dir_path, 'types')

font_dir_path = os.path.join(script_path, 'fonts')


#from Pokemon import pokemon as p
#from epd.lib import epd2in13g #Waveshare
#import inkyphat #Pimoroni inky phat

logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

'''
def new_epd() -> epd2in13g:
    try:
        logging.info("Starting epd2in13g Demo")

        #epd = epd2in13g.EPD()
    except IOError as e:
        logging.info(e)
        print(traceback.format_exc())
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        epd2in13g.epdconfig.module_exit(cleanup=True)
        exit()
    
    return epd
'''

def convert_transparent_to_white_file(image_path: str, new_format: str = 'jpg') -> str:
    '''Converts an image to a new format and returns the new image's path
    
    image_path - path to the image to convert
    new_format - new format to use for the image
    
    returns a string that contains the path to the new image
    '''
    #https://stackoverflow.com/questions/50898034/how-replace-transparent-with-a-color-in-pillow
    image = Image.open(image_path)

    # Create a white rgba background
    new_image = Image.new("RGBA", image.size, "WHITE") 
    
    # Paste the image on the background.
    new_image.paste(image, (0, 0), image)              
    
    dir, file = os.path.split(image_path)
    file_name = re.sub(r'\.[a-zA-Z0-9]+$', '', file)
    file_name = f"{file_name}.{new_format}"

    # Save as JPEG
    new_image.convert('RGB').save(file_name, "JPEG")  

    return os.path.join(dir, file_name)


def new_epd(flip: bool = False, flip_x: bool = False, flip_y: bool = False):
    logging.info("Initializing inky phat")

    try:
        from inky.auto import auto
    except TypeError:
        raise TypeError("You need to update the Inky library to >= v1.1.0")
    except ImportError:
        logging.warning("Inky library required for this script")
        exit('Inky library required for this script')
    inky_display = auto()
    inky_display.set_border(inky_display.WHITE)

    if flip or flip_x:
        inky_display.h_flip = True
    
    if flip or flip_y:
        inky_display.v_flip = True

    return inky_display


#####
# Pokemon Data Functions
#####

def get_pokemon_list_file(file_path: str = pokemon_list_path) -> Optional[list]:
    '''Get the cache file with a list of all pokemon names & dex numbers

    file_path - path to the json file containing pokemon names & dex numbers

    returns JSON-formatted list 
    '''
    try:
        with open(file_path,'r') as f:
            contents = ''.join(f.readlines())
        #pokemon_list = json.loads(f.readlines())
        pokemon_list = json.loads(contents)
        logging.info(f"Got list of {len(pokemon_list)} entries")
    except FileNotFoundError:
        logging.warning(f"[!]File not found: {file_path}")
        pokemon_list = None
    except Exception as e:
        logging.warning(f"error: {e}")
        pokemon_list = None
    return pokemon_list


def get_pokemon_data(pokemon:(int,str)) -> Optional[dict]:
    '''Checks for a cached pokemon data file

    pokemon - a pokemon's name or dex number to query

    returns a JSON-formatted object of pokemon data
    '''

    #Check our dex entries to see if it's cached
    dex_files = os.listdir(dex_dir_path)
    filename = f'{pokemon}.json'
    if filename in dex_files:
        file_path = os.path.join(dex_dir_path, filename)
        try:
            with open (file_path) as f:
                pokemon_data = json.loads(''.join(f.readlines()))
            logging.info(f"Got data for {pokemon_data['name']}")
        except Exception as e:
            logging.info(f'Failed to get data for {pokemon}')
            logging.warning(f'Error: {e}')
            pokemon_data = None
    else:
        logging.info(f"No data file for {pokemon}")
        pokemon_data = None

    #TODO: check last queried date & update if needed
    
    return pokemon_data


def get_pokemon_sprite_png_path(pokemon:(int, str)) -> str:
    '''Get's the path to a pokemon's sprite file
    
    pokemon - a pokemon's name or dex number
    
    returns the path to the sprite file'''

    sprite_path = os.path.join(pokemon_sprites_path, f'{pokemon}.png')
    return sprite_path


#####
# Image functions
#####

def create_pokemon_info_text(pokemon_data: dict, canvas_size: tuple[int], font: ImageFont, canvas_color: str="WHITE", font_color: str="BLACK") -> Image:
    logging.debug(f"Creating info text of size {canvas_size}")
    #Create the canvas for pkmn info 
    canvas = Image.new("RGBA", canvas_size, canvas_color)
    info_txt = ImageDraw.Draw(canvas)
    
    #Dex number and name
    pokemon_name = pokemon_data['name'][0].upper() + pokemon_data['name'][1::]
    pokemon_id = f"{pokemon_data['id']}"
    info_txt_str = f"No. {pokemon_id}\n{pokemon_name}"
    logging.debug(f"Writing pokemon data: {info_txt_str}")
    info_txt_x = 10
    info_txt_y = 20
    bbox = info_txt.multiline_textbbox((info_txt_x, info_txt_y), info_txt_str, font=font)
    info_txt.multiline_text((info_txt_x, info_txt_y), info_txt_str, font_color, font=font)
    info_txt_y += bbox[3] + 20
    
    #Type icon(s)
    type_canvas_size = (canvas_size[0], int(canvas_size[1]))
    type_info_canvas = create_pokemon_type_info(pokemon_data, type_canvas_size, font, canvas_color, font_color)
    canvas.paste(type_info_canvas, (info_txt_x, info_txt_y), type_info_canvas)

    canvas = canvas.convert("RGB")

    #Save canvas for debugging
    #canvas_path = os.path.join(script_path, f"test-info-canvas.png")
    #logging.debug(f"Saving canvas to {canvas_path}")
    #canvas.save(canvas_path)

    return canvas


def create_pokemon_type_info(pokemon_data: dict, canvas_size: tuple[int], font: ImageFont, canvas_color: str="WHITE", font_color: str="BLACK") -> Image:
    logging.debug(f"Creating type info canvas of size {canvas_size}")
    #Create the canvas for pkmn info 
    canvas = Image.new("RGBA", canvas_size, canvas_color)
    type_info = ImageDraw.Draw(canvas)

    #Coords
    type_sprite_y = 0
    type_sprite_x = 0
    type_sprite_indent = 20

    #Type text & icon(s)
    for pkmn_type_dict in pokemon_data['types']:
        #Type header
        type_text = f"Type {pkmn_type_dict['slot']}/"
        bbox = type_info.textbbox((type_sprite_x, type_sprite_y), type_text, font=font)
        type_info.text((type_sprite_x, type_sprite_y), type_text, font=font, fill=font_color)
        type_sprite_y = bbox[3] + 10
        
        #Type sprite
        pkmn_type_str = pkmn_type_dict['type']['name']
        type_sprite = Image.open(os.path.join(types_sprites_path, f"{pkmn_type_str}.png"))
        logging.info(f"Imported sprite of type {pkmn_type_str} & size {type_sprite.width}x{type_sprite.height}")
        canvas.paste(type_sprite, (type_sprite_x + type_sprite_indent, type_sprite_y), type_sprite)
        #type_sprite_y += type_sprite.height + 10
        type_sprite_x += type_sprite.width + type_sprite_indent
        type_sprite_y = 0
    
    #Save canvas for debugging
    canvas_path = os.path.join(script_path, f"test-type-canvas.png")
    logging.debug(f"Saving type canvas to {canvas_path}")
    canvas.save(canvas_path)
    
    return canvas


def create_pokemon_dex_text(pokemon_data: dict, canvas_size: tuple, canvas_color: str="WHITE", font_path: str=font_dir_path, font_size: int=24, font: ImageFont=None, font_color: str="BLACK") -> Image:
    logging.debug(f"Creating dex text of size {canvas_size}")
    #Create the info text
    canvas = Image.new("RGBA", size=canvas_size, color=canvas_color)
    dex_txt = ImageDraw.Draw(canvas)

    if not font:
        font = ImageFont.truetype(font_path, font_size)
    
    #What are we writing?
    flavor_text_list = list(set(entry['flavor_text'] for entry in pokemon_data['flavor_text_entries'] if entry['language']['name'] == 'en')) #Convert to set to dedupe
    flavor_text = choice(flavor_text_list)
    flavor_text = flavor_text.replace('\n', ' ')
    logging.debug(f"Writing flavor text: {flavor_text}")

    #Calculate how big the textbox will be. If it's too big, wrap to a new line
    dex_pos_y = 10
    dex_pos_x = 10
    max_txt_size_x = canvas_size[0] - 10
    max_txt_size_y = canvas_size[1] - 20
    line_spacing=8
    
    while True:
        text = []
        for word in flavor_text.split(" "):
            text.append(word)

            #How's it look?
            txt_str = '  '.join(text)
            bbox = dex_txt.multiline_textbbox((dex_pos_x, dex_pos_y), txt_str, font=font, spacing=line_spacing)
            #bbox indices: [left, top, right, bottom]

            #Check if the text is too wide
            if bbox[2] > max_txt_size_x:
                #text[len(text)-2] = f"{text[len(text)-2]}\n"
                text[len(text)-1] = f"\n{text[len(text)-1]}"
        
        #Check if text is too tall
        txt_str = '  '.join(text)
        bbox = dex_txt.multiline_textbbox((dex_pos_x, dex_pos_y), txt_str, font=font)

        #Good enough, lets leave
        if bbox[3] < max_txt_size_y:
            break
        
        #Smaller font that might fit
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        

    #Fill in the last bit
    dex_txt.multiline_text((dex_pos_x, dex_pos_y), txt_str, fill=font_color, font=font, spacing=line_spacing)

    #Save for debugging
    canvas_path = os.path.join(script_path, f"test-dex-canvas.png")
    logging.debug(f"Saving canvas to {canvas_path}")
    canvas.save(canvas_path)

    return canvas


def quantize_image(palette_list: list, image: Image) -> Image:
    #Quantize the image so that it works with EPDs limited colors/palette
    palette = Image.new("P", (1, 1))
    inky_palette = [value for rgb in palette_list for value in rgb]
    inky_palette += [0,0,0] * (256 - int(len(inky_palette) / 3))
    palette.putpalette(inky_palette)
    '''palette.putpalette(
    [
        255, 255, 255,   # 0 = White
        0, 0, 0,         # 1 = Black
        255, 255, 0,       # 2 = Red (255, 255, 0 for yellow)
    ] + [0, 0, 0] * 253  # Zero fill the rest of the 256 colour palette
    )'''

    if image.mode != "RGB":
        image = image.convert("RGB")
    
    return image.quantize(colors=int(len(inky_palette) / 3), palette=palette)


#####
# Pimoroni Functions
#####

def create_mask(source, mask=(0,1,2)): #=(inky_display.WHITE, inky_display.BLACK, inky_display.YELLOW)):
    """Create a transparency mask.

    Takes a paletized source image and converts it into a mask
    permitting all the colours supported by Inky pHAT (0, 1, 2)
    or an optional list of allowed colours.
    :param mask: Optional list of Inky pHAT colours to allow.
    """
    mask_image = Image.new("1", source.size)
    w, h = source.size
    for x in range(w):
        for y in range(h):
            p = source.getpixel((x, y))
            if p in mask:
                mask_image.putpixel((x, y), 255)

    return mask_image


def main():
    #Parse args
    parser = argparse.ArgumentParser(
        prog='EPD Pokedex',
        description='Displays Pokemon data on an E-Paper Display'
    )
    parser.add_argument('--epd-color', '-epd', default='yellow', metavar='epd_color')
    parser.add_argument('--pokemon', '-p')

    args = parser.parse_args()

    #Initialize the EPD
    inky_display = new_epd(flip=True)

    if args.pokemon:
        pokemon = args.pokemon
        pokemon_data = get_pokemon_data(pokemon)
        sprite_path = get_pokemon_sprite_png_path(pokemon)

        if os.path.exists(sprite_path):
            logging.info(f"Got sprite: {pokemon_data['id']} - {pokemon_data['name']}")
        else:
            logging.info(f"No sprite found for {pokemon}")
            exit()
    else:
        pokemon_list = get_pokemon_list_file()
        while True:
            logging.info('Getting random pokemon')
            #Get the pokemon info
            pokemon = choice(list(pokemon_list.values()))
            pokemon_data = get_pokemon_data(pokemon)
            sprite_path = get_pokemon_sprite_png_path(pokemon)

            if os.path.exists(sprite_path):
                logging.info(f"Got sprite: {pokemon_data['id']} - {pokemon_data['name']}")
                break
            else:
                logging.info(f"No sprite found for {pokemon}")
    

    #Prep the backdrop
    backdrop = Image.new("RGB", (inky_display.width, inky_display.height), "WHITE")

    #Prep the sprite
    sprite = Image.open(sprite_path)
    sprite = sprite.resize((250, 250))
    
    #PIL defaults transparent backgrounds to black, so lets fix that
    sprite = sprite.convert("RGBA")
    sprite_background = Image.new("RGBA", (inky_display.width, inky_display.height), "WHITE") # Create a white rgba background
    sprite_background.paste(sprite, (0,0), sprite) # Paste the image on the background
    
    '''
    #Quantize the image so that it works with EPDs limited colors/palette
    palette = Image.new("P", (1, 1))
    inky_palette = [value for rgb in inky_display_DESATURATED_PALETTE for value in rgb]
    inky_palette += [0,0,0] * (256 - int(len(inky_palette) / 3))
    palette.putpalette(inky_palette)
    '''
    '''palette.putpalette(
    [
        255, 255, 255,   # 0 = White
        0, 0, 0,         # 1 = Black
        255, 255, 0,       # 2 = Red (255, 255, 0 for yellow)
    ] + [0, 0, 0] * 253  # Zero fill the rest of the 256 colour palette
    )
    '''
    '''
    sprite_background = sprite_background.quantize(colors=len(inky_display_DESATURATED_PALETTE), palette=palette)
    '''
    sprite_background = quantize_image(inky_display.DESATURATED_PALETTE, sprite_background).convert('RGBA')
    backdrop.paste(sprite_background, (0,0), sprite_background)

    #Import font(s)
    font_path = os.path.join(font_dir_path, 'pkmn.ttf')
    logging.debug(f"Getting font from {font_path}")
    pkmn_font24 = ImageFont.truetype(font_path, 24)

    #Create the info text section and apply it to the backdrop
    info_txt_width = inky_display.width - sprite.width
    info_txt_height = inky_display.height - sprite.height
    logging.debug(f"Info text width: {info_txt_width} ({inky_display.width} - {sprite.width})")
    logging.debug(f"Info text height: {info_txt_height} ({inky_display.height} - {sprite.height})")
    info_txt = create_pokemon_info_text(pokemon_data, (info_txt_width, info_txt_height), font=pkmn_font24)
    info_txt = quantize_image(inky_display.DESATURATED_PALETTE, info_txt).convert("RGBA")
    info_start_x = sprite.width + 5
    info_start_y = 0
    logging.debug(f"Placing info img at ({info_start_x},{info_start_y})")
    backdrop.paste(info_txt, (info_start_x, info_start_y), info_txt) #Change to actual coords

    #Create the dex text and apply it to the backdrop
    dex_txt = ImageDraw.Draw(sprite)
    dex_txt_width = inky_display.width
    dex_txt_height = inky_display.height - sprite.height
    logging.debug(f"Dex text width: {dex_txt_width} ({inky_display.width})")
    logging.debug(f"Dex text height: {dex_txt_height} ({inky_display.height} - {sprite.height})")
    dex_txt = create_pokemon_dex_text(pokemon_data, (dex_txt_width, dex_txt_height), font_path=font_path)
    dex_start_x = 0
    dex_start_y = sprite.height
    logging.debug(f"Placing dex img at ({dex_start_x},{dex_start_y})")
    backdrop.paste(dex_txt, (dex_start_x, dex_start_y), dex_txt)

    #Draw lines for aesthetics - horizontal between sprite and dex
    line_draw = ImageDraw.Draw(backdrop)
    line_start_x = 0
    line_end_x = inky_display.width
    line_start_y = sprite.height + 1
    line_end_y = sprite.height + 1
    line_draw.line(((line_start_x, line_start_y),(line_end_x, line_end_y)), fill="BLACK", width=5)
    line_draw.line(((line_start_x, line_start_y + 6),(line_end_x, line_end_y + 6)), fill="BLACK", width=1)

    #Draw some more lines for aesthetics - vertical between sprite and type
    line_start_x = sprite.width + 1
    line_end_x = sprite.width + 1
    line_start_y = 0
    line_end_y = sprite.height
    line_draw.line(((line_start_x, line_start_y),(line_end_x, line_end_y)), fill="BLACK", width=5)
    line_draw.line(((line_start_x + 6, line_start_y),(line_end_x + 6, line_end_y)), fill="BLACK", width=1)
    
    #Save it to check
    backdrop_path = os.path.join(script_path, f"{pokemon}.png")
    #backdrop.save(backdrop_path)

    inky_display.set_image(backdrop)

    # And show it!
    logging.info('Showing image on EPD')
    inky_display.show()
    
    '''
    sprite_img = Image.open(sprite_path, mode='RGBA')

    #Create the Text
    txt_img_size = (80,65)
    txt_img = Image.new('RGB', txt_img_size, (255,255,255))
    txt = ImageDraw.Draw(txt_img)
    txt.text((0,0), f'#{pokemon_data['id']}', font=font24, fill=(0,0,0))
    txt.text((0,30),f"{pokemon_data['name']}", font=font24, fill=(0,0,0))
    r_txt = txt_img.rotate(270, expand=1)
    
    #Combine the picture & text
    sprite_img.paste(r_txt, (30, 140))

    #Send it to the EPD
    new_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{pokemon_data['id']}.bmp')
    sprite_img.save(new_name)
    #epd.display(epd.getbuffer(sprite_img))
    '''


if __name__ == '__main__':
    main()