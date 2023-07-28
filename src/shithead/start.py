"""
Starting Screen.

Arcade view showing the title screen.
Writes 'Masters of' at the top of the screen.
Next 'SHITHEAD' is written with face down cards in an animated sequence from
left to write followed by flipping the cards over from right to left.
Finally we get a line with the version, a 'Programmed with ...'
and a 'Game Assets from ...' statement.
At the bottom of the screen the buttons to open additional screens with English
and German rules and the 'CONTINUE' button, which brings us to the
configuration screen, are placed.
Position and angle for the card sprites used in the title animation are loaded
from a json file.
Pressing the 'RULES' or 'REGELN' button each starts a 'rules.py' subprocess
(Popen) which loads either the English or the German rules from the
corresponding json file.

23.04.2023 Wolfgang Trachsler
"""



import arcade
import subprocess
import json
import pkgutil
import os
import sys
import platform

# local imports (modules in same package)
from .cards import Card, Deck
from .gui import CardSprite
from . import config
from . import rules

VERSION = '1.0.3'

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Sh*thead"

DEFAULT_LINE_HEIGHT = 18
DEFAULT_FONT_SIZE = 12
COLOR = arcade.color.WHITE

# dimensions of buttons
BUTTON_SCALE = 0.7
BUTTON_RELEASED = ":resources:gui_basic_assets/red_button_normal.png"
BUTTON_PRESSED = ":resources:gui_basic_assets/red_button_press.png"

# position of Version
VERSION_Y = 444

# Position of Buttons
ENGLISH_X = SCREEN_WIDTH / 4
GERMAN_X = SCREEN_WIDTH * 2 / 4
CONTINUE_X = SCREEN_WIDTH * 3 / 4
BUTTON_Y = SCREEN_HEIGHT / 5

# result view states
IDLE_STATE = 0          # no button pressed
ENGLISH_STATE = 1       # 'RULES' button pressed
GERMAN_STATE = 2        # 'REGELN' button pressed
CONTINUE_STATE = 3      # 'CONTINUE' button pressed

# scale of cards used in title
CARD_SCALE = 0.16

# File containing position and angle of card sprites for title animation.
TITLE_FILE = 'title.json'

class StartView(arcade.View):
    '''
    View where we show the the title of the game.
    '''

    def __init__(self):
        '''
        Initializer.
        '''

        super().__init__()

        # set the background color to amazon green.
        arcade.set_background_color(arcade.color.AMAZON)

        # list holding cards for title after creation, not shown yet
        self.card_list = []

        # create a sprite list for the animated title sequence
        self.title = arcade.SpriteList()
        self.title_index = 0    # counter for animation
        self.title_fup = False  # True => face up animation
        self.title_len = 0      # number of cards in title

        # create text list
        self.text_list = []

        # create a sprite list for the 'RULES', 'REGELN' and 'CONTINUE' buttons.
        self.button_list = arcade.SpriteList()
        self.english = None         # 'RULES' button
        self.german = None          # 'REGELN' button
        self.config = None          # 'CONTINUE' button
        self.state = IDLE_STATE     # no button pressed

    def setup_text_objects(self):
        """
        Setup the text objects.
        We create a text object for the 'Masters of' which appears before the
        main title (which is not a text object but a set of card sprites).
        After the main title, there will be the version and some additional
        information.
        """
        # create the main title text object
        start_x = 0
        start_y = SCREEN_HEIGHT - DEFAULT_LINE_HEIGHT * 2.5
        text = arcade.Text('Masters of', start_x, start_y,
                arcade.color.BRIGHT_GREEN, DEFAULT_FONT_SIZE * 2,
                width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

#        # 'SHITHEAD' text object, replaced with card sprites
#        start_y = text.bottom - DEFAULT_LINE_HEIGHT * 10
#        text = arcade.Text('SHITHEAD', start_x, start_y,
#                arcade.color.CINNABAR, DEFAULT_FONT_SIZE * 12,
#                width=SCREEN_WIDTH, align='center')
#        self.text_list.append(text)

        # create version text object
        start_y =  VERSION_Y
        text = arcade.Text(VERSION, start_x, start_y,
                arcade.color.WHITE, DEFAULT_FONT_SIZE,
                width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

        # create programmed with ... text object
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('Programmed with Python3/Arcade Library', start_x, start_y,
                arcade.color.WHITE, DEFAULT_FONT_SIZE,
                width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

        # create game assets from ... text object
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('Game Assets from kenney.nl', start_x, start_y,
                arcade.color.WHITE, DEFAULT_FONT_SIZE,
                width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

    def setup_main_title(self):
        """
        Creates cards used to form the main title.

        We use playing cards to write out the main title 'SHITHEAD' in large
        letters. Position and angle for each card is has been generated with an
        additional tool and can be loaded from a json file.
        To have different cards in the title each time we start the program,
        we create 6 decks (we need 220 cards but want an even distribution of
        red and blue backs) and shuffle them. From these cards we then create
        the card sprites (initially face down) with the loaded position and
        angles.
        """
        # load coords of cards forming the title
        try:
            data = pkgutil.get_data(__package__, TITLE_FILE)
        except OSError as exception:
            print(f"### Error couldn't load file {TITLE_FILE}")
            return

        # deserialize the json data
        title_coords = json.loads(data)

        # determine the number of cards in the title
        self.title_len = len(title_coords)

        # create 6 Decks and shuffle them
        # we need 220 cards but want an even distribution of red and blue backs
        cards = Deck(0)
        for i in range(1, 6):
            cards += Deck(i)
        cards.shuffle()

        # for each set of coords/angle in title_coords create a sprite
        # (face down) and add it to the card list.
        for coord in title_coords:
            card = cards.pop_card()
            card_sprite = CardSprite(card, CARD_SCALE)
            card_sprite.position = (coord[0], coord[1])
            card_sprite.angle = coord[2]
            self.card_list.append(card_sprite)

    def setup_english_rules_button(self):
        """
        Creates 'RULES' button sprite and text object.

        Creates a button sprite.
        Adds the created button sprite to the button sprite list.
        Creates the 'RULES' text object and adds it to the text object list.
        """
        self.english = arcade.Sprite(BUTTON_RELEASED, BUTTON_SCALE, hit_box_algorithm='None')
        self.english.position = (ENGLISH_X, BUTTON_Y)
        self.button_list.append(self.english)

        # create button text
        text = arcade.Text(
            'RULES',
            ENGLISH_X,
            BUTTON_Y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')
        self.text_list.append(text)

    def setup_german_rules_button(self):
        """
        Creates 'REGELN' button sprite and text object.

        Creates a button sprite.
        Adds the created button sprite to the button sprite list.
        Creates the 'REGELN' text object and adds it to the text object list.
        """
        self.german = arcade.Sprite(BUTTON_RELEASED, BUTTON_SCALE, hit_box_algorithm='None')
        self.german.position = (GERMAN_X, BUTTON_Y)
        self.button_list.append(self.german)

        # create button text
        text = arcade.Text(
            'REGELN',
            GERMAN_X,
            BUTTON_Y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')
        self.text_list.append(text)

    def setup_continue_button(self):
        """
        Creates 'CONTINUE' button sprite and text object.

        Creates a button sprite.
        Adds the created button sprite to the button sprite list.
        Creates the 'CONTINUE' text object.
        """
        self.config = arcade.Sprite(BUTTON_RELEASED, BUTTON_SCALE, hit_box_algorithm='None')
        self.config.position = (CONTINUE_X, BUTTON_Y)
        self.button_list.append(self.config)

        # create button text
        text = arcade.Text(
            'CONTINUE',
            CONTINUE_X,
            BUTTON_Y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')
        self.text_list.append(text)

    def setup(self):
        # setup the cards for the main title
        self.setup_main_title()
        # setup the text objects
        self.setup_text_objects()
        # setup the 'RULES', 'REGELN', and 'CONTINUE' buttons
        self.setup_english_rules_button()
        self.setup_german_rules_button()
        self.setup_continue_button()

    def on_mouse_press(self, x, y, button, key_modifiers):
        """
        Mouse button pressed event callback function.

        This function is called when the mouse button was pressed.
        We check if the mouse was clicked on the 'RULES', 'REGELN' or 'CONTINUE'
        button and change the button image to reflect the pressed state.
        Change the state according to the button press.

        :param x:               X-coord of mouse when button was pressed.
        :type x:                float
        :param y:               Y-coord of mouse when button was pressed.
        :type y:                float
        :param button:          the mouse button which was pressed.
        :type button:           int
        :param key_modifiers:   TODO
        :type key_modifiers:    int
        """
        # check if we have pressed the button
        button = arcade.get_sprites_at_point((x,y), self.button_list)
        if len(button) > 0:
            # mouse clicked on one of the buttons
            if button[0] == self.english:
                # clicked the 'RULES' button
                self.english.texture = arcade.load_texture(BUTTON_PRESSED)
                self.state = ENGLISH_STATE
            elif button[0] == self.german:
                # clicked the 'REGELN' button
                self.german.texture = arcade.load_texture(BUTTON_PRESSED)
                self.state = GERMAN_STATE
            else:
                # clicked the 'CONTINUE' button
                self.config.texture = arcade.load_texture(BUTTON_PRESSED)
                self.state = CONTINUE_STATE
        else:
            # none of the buttons clicked
            self.state = IDLE_STATE

    def on_mouse_release(self, x, y, button, key_modifiers):
        """
        Mouse button released event callback function.

        This function is called when the mouse button was released.

        :param x:               X-coord of mouse when button was released.
        :type x:                float
        :param y:               Y-coord of mouse when button was released.
        :type y:                float
        :param button:          the mouse button which was released.
        :type button:           int
        :param key_modifiers:   TODO
        :type key_modifiers:    int
        """
        # HACK to get paths to rules.py, rules_eng.json, and rules_ger.json
        # TODO find a better way
        rules_dir = os.path.dirname(rules.__file__)
        rules_prg = os.path.join(rules_dir, 'rules.py')
        if platform.system() == 'Linux':
            # set files with Linux specific parameters (size, font)
            rules_eng = os.path.join(rules_dir, 'rules_eng.json')
            rules_ger = os.path.join(rules_dir, 'rules_ger.json')
        else:
            # set files with Windows specific parameters (size, font)
            rules_eng = os.path.join(rules_dir, 'ms_rules_eng.json')
            rules_ger = os.path.join(rules_dir, 'ms_rules_ger.json')

        # load the released button image into all button sprites
        self.english.texture = arcade.load_texture(BUTTON_RELEASED)
        self.german.texture = arcade.load_texture(BUTTON_RELEASED)
        self.config.texture = arcade.load_texture(BUTTON_RELEASED)
        # execute the action of the pressed button
        if self.state == ENGLISH_STATE:
            # open window with english rules
            if os.path.basename(sys.executable) == 'shithead.exe':
                # pyinstaller executable for windows
                # shithead.exe -r ms_rules_eng.json
                subprocess.Popen([sys.executable, '-r', rules_eng])
            elif os.path.basename(sys.executable) == 'shithead':
                # pyinstaller executable for linux
                # shithead -r rules_eng.json
                subprocess.Popen([sys.executable, '-r', rules_eng])
            else:
                # python3 rules.py rules_eng.json
                subprocess.Popen([sys.executable, rules_prg, rules_eng])
        elif self.state == GERMAN_STATE:
            # open window with german rules
            if os.path.basename(sys.executable) == 'shithead.exe':
                # pyinstaller executable for windows
                # shithead.exe -r ms_rules_ger.json
                subprocess.Popen([sys.executable, '-r', rules_ger])
            elif os.path.basename(sys.executable) == 'shithead':
                # pyinstaller executable for windows
                # shithead -r rules_ger.json
                subprocess.Popen([sys.executable, '-r', rules_ger])
            else:
                # python3 rules.py rules_ger.json
                subprocess.Popen([sys.executable, rules_prg, rules_ger])
        elif self.state == CONTINUE_STATE:
            # load the config view into this window
            config_view = config.ConfigView()
            # set up the config view
            config_view.setup()
            # and make it the view shown in the window
            self.window.show_view(config_view)
        else:
            pass
#            print("None of the buttons pressed")

    def on_draw(self):
        """
        Render the screen callback function.

        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        # clear the screen
        self.clear()

        # we want the 'Masters of' text to appear first
        self.text_list[0].draw()

        # the title 'SHITHEAD' appears as animated sequence
        if self.title_index < self.title_len and not self.title_fup:
            # 1st we add cards face down to the title from left to right
            self.title.append(self.card_list.pop(0))
            self.title_index += 1
        elif self.title_index == self.title_len and not self.title_fup:
            self.title_fup = True
        elif self.title_index > 0 and self.title_fup:
            # then we turn the cards face up from right to left
            self.title[self.title_index - 1].face_up()
            self.title_index -= 1
        else:
            # draw buttons
            self.button_list.draw()

            # draw remaining texts (including button labels)
            for text in self.text_list:
                text.draw()

        # display cards forming the 'SHITHEAD' title.
        self.title.draw()

def main():

    # testing the config view
    # open a window with predefined size and title
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    # create the StartView
    start_view = StartView()
    # and make it the view shown in the window
    window.show_view(start_view)
    # setup the StartView
    start_view.setup()

    # start
    arcade.run()

if __name__ == "__main__":
    main()
