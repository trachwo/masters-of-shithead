
"""
Result screen of shithead game.

As soon as the shithead of the round has been found in the GameView,
the ResultView will be setup and will be made the active view.
It shows a statistics table with an overview over all results found with this
player configuration and the last shithead marked in red.
It also provides a 'NEXT GAME' button to start the next round
and an 'EXIT GAME' button to leave the game.

06.02.2023 Wolfgang Trachsler
"""

import arcade
import sys

# local imports (modules in same package)
from .stats import Statistics
from . import config

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Sh*thead"

# Card size
CARD_SCALE = 0.5
CARD_WIDTH = int(140 * CARD_SCALE)
CARD_HEIGHT = int(190 * CARD_SCALE)

DEFAULT_FONT_SIZE = 14
TEXT_FONT_SIZE = 14

# Position of instructional message
RESULT_X = 400
RESULT_Y = 600
LINE_SPACING = 30

NAME_WIDTH = 200
SH_COUNT_WIDTH = 100
SH_PERCENT_WIDTH = 100
SCORE_WIDTH = 100
GAMES_WIDTH = 100
TURNS_WIDTH = 100
AVG_TURNS_WIDTH = 80
LINE_HEIGHT = 30

TITLE_WIDTHS = [NAME_WIDTH, SH_COUNT_WIDTH + SH_PERCENT_WIDTH, SCORE_WIDTH,
                GAMES_WIDTH, TURNS_WIDTH + AVG_TURNS_WIDTH]
TITLE_ALIGNS = ['center', 'center', 'center', 'center', 'center' ]
TITLE_TEXTS = ['PLAYERS', 'SHITHEADS', 'SCORE', 'GAMES', 'TURNS']
ENTRY_WIDTHS = [NAME_WIDTH, SH_COUNT_WIDTH, SH_PERCENT_WIDTH, SCORE_WIDTH,
                GAMES_WIDTH, TURNS_WIDTH, AVG_TURNS_WIDTH]
ENTRY_ALIGNS = ['left', 'right', 'right', 'right', 'right', 'right', 'right']
TEXT_MARGIN = 10
TABLE_WIDTH = sum(TITLE_WIDTHS)

# scale and images used for buttons
BUTTON_SCALE = 0.7
BUTTON_RELEASED = ":resources:gui_basic_assets/red_button_normal.png"
BUTTON_PRESSED = ":resources:gui_basic_assets/red_button_press.png"

# Position of 'NEXT GAME' and 'EXIT GAME' Buttons
NEXT_X = SCREEN_WIDTH / 3
EXIT_X = SCREEN_WIDTH * 2 / 3
BUTTON_Y = SCREEN_WIDTH / 5

# result view states
IDLE_STATE = 0  # no button pressed
NEXT_STATE = 1  # 'NEXT GAME' button pressed
EXIT_STATE = 2  # 'EXIT_GAME' button pressed


class ResultLine:

    def __init__(self, upper_left, height, color, border, fields):
        """
        Create a result table line.

        :param upper_left:      coords of upper left corner
        :type upper_left_x:     tuple
        :param heigth:          height of line
        :type height:           int
        :param color:           border/text color
        :type color:            tuple of arcade.color
        :param border:          size of border
        :typer border:          int
        :param fields:          list of field specs (width, align, text).
        :type widths:           list
        """
        self.frames = []
        self.texts = []
        frame_color, text_color = color
        x, y = upper_left       # coords of upper left corner
        y -=  height / 2        # center y-coord of line
        for field in fields:
            # unpack field specification from tuple
            width, align, content = field
            # calculate x-coord of center of this rectangle
            x += width / 2
            # create this rectangle
            frame = arcade.create_rectangle_outline(
                    x,          # x-coord of rectangle center
                    y,          # y-coord of rectangle center
                    width,      # width of rectangle
                    height,     # height of rectangle
                    frame_color, # color of rectangle outline
                    border,     # size of border
                    0)          # tilt angle
            # and add it to the list of frames
            self.frames.append(frame)

            # create text object for field content
            if align == 'left':
                x_text = x - width / 2 + TEXT_MARGIN
            elif align == 'right':
                x_text = x + width / 2 - TEXT_MARGIN
            else:
                x_text = x
            text = arcade.Text(
                    content,
                    x_text,
                    y,
                    text_color,
                    DEFAULT_FONT_SIZE,
                    anchor_x= align,
                    anchor_y='center')
            # and add it to the list of texts
            self.texts.append(text)

            # calculate x-coord of left edge of next rectangle
            x += width / 2

    def draw(self):
        # draw line frames
        for frame in self.frames:
            frame.draw()
        # draw line content
        for text in self.texts:
            text.draw()

class ResultTable:

    def __init__(self, upper_left, stats, shithead):
        """
        Create the result table from the game statistics.

        :param upper_left:  coord of upper left corner of result table.
        :type upper_left:   tuple
        :param stats:       game statistics
        :type stats:        Statistics
        :param shithead:    name of last shithead.
        :type shithead:     str
        """
        self.lines = []                 # list of result table lines
        self.upper_left = upper_left    # set coords of upper left corner
        self.stats = stats              # set game statistics

        x, y = upper_left
        # get list of table entries
        tab = stats.get_table()
        table_height = (len(tab) + 1) * LINE_HEIGHT
        # create a rectangle framing the whole table
        frame = arcade.create_rectangle_outline(
                x + TABLE_WIDTH / 2,    # x-coord
                y - table_height / 2,   # y-coord
                TABLE_WIDTH,            # width of rectangle
                table_height,           # height of rectangle
                arcade.color.WHITE,     # color of rectangle outline
                3,                      # size of border
                0)                      # tilt angle
        self.lines.append(frame)

        # create the title line
        fields = zip(TITLE_WIDTHS, TITLE_ALIGNS, TITLE_TEXTS)
        # tuple with frame and text color
        color = (arcade.color.WHITE, arcade.color.BRIGHT_GREEN)
        line = ResultLine(upper_left, LINE_HEIGHT, color, 3, fields)
        self.lines.append(line)

        # add lines with content of table
        for entry in tab:
            if entry == tab[-1]:
                border = 3
            else: border = 1
            if entry[0] == shithead:
                color = (arcade.color.WHITE, arcade.color.CINNABAR)
            else:
                color = (arcade.color.WHITE, arcade.color.WHITE)
            fields = zip(ENTRY_WIDTHS, ENTRY_ALIGNS, entry)
            y -= LINE_HEIGHT
            line = ResultLine((x,y), LINE_HEIGHT, color, border, fields)
            self.lines.append(line)

    def draw(self):
        for line in self.lines:
            line.draw()


class ResultView(arcade.View):
    '''
    View where we show the result and the game statistics.
    '''

    def __init__(self):
        """
        Result view initializer.
        """
        # Initializes the super class
        super().__init__()

        self.config = None          # game configuration
        self.stats = None           # game statistics
        self.shithead = None        # shithead of last game
        self.table = None           # result table
        self.next = None            # next game button
        self.exit = None            # exit game button
        self.button_list = None     # sprite list for buttons
        self.state = IDLE_STATE     # no button pressed

        # set the background color to amazon green.
        arcade.set_background_color(arcade.color.AMAZON)

    def setup_next_button(self):
        """
        Creates 'NEXT GAME' button sprite and text object.

        Creates a button sprite.
        Adds the created button sprite to the button sprite list.
        Creates the 'NEXT GAME' text object.
        """
        self.next = arcade.Sprite(BUTTON_RELEASED, BUTTON_SCALE, hit_box_algorithm='None')
        self.next.position = (NEXT_X, BUTTON_Y)
        self.button_list.append(self.next)

        # create button text
        self.next_text = arcade.Text(
            'NEXT GAME',
            NEXT_X,
            BUTTON_Y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')

    def setup_exit_button(self):
        """
        Creates 'EXIT GAME' button sprite and text object.

        Creates a button sprite.
        Adds the created button sprite to the button sprite list.
        Creates the 'EXIT GAME' text object.
        """
        self.exit = arcade.Sprite(BUTTON_RELEASED, BUTTON_SCALE, hit_box_algorithm='None')
        self.exit.position = (EXIT_X, BUTTON_Y)
        self.button_list.append(self.exit)

        # create button text
        self.exit_text = arcade.Text(
            'EXIT GAME',
            EXIT_X,
            BUTTON_Y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')

    def setup(self, stats, shithead, config):
        """
        Setup the result view.

        The result view consists of result table showing the game statistics,
        a 'next game' button, and an 'exit game' button.

        :param stats:       game statistics.
        :type stats:        Statistics
        :param shithead;    shithead of the last game => marked red in result.
        :type shithead:     str
        :param config:      game configuration.
        :type config:       dict.
        """
        # store the configuration => necessary to start the next game
        self.config = config
        # set statistics => result table
        self.stats = stats
        # set shithead of last game => result table and dealer of next game
        self.shithead = shithead
        # get number of players
        # to calculate the Y-coord of the upper left corner.
        n_players = stats.get_nof_players()
        # calculate table height from number of players + title and footer line
        table_height = (n_players + 2) * LINE_HEIGHT
        # calculate the coords of the upper left corner of the result table
        upper_left = ((SCREEN_WIDTH - TABLE_WIDTH) / 2,
                SCREEN_HEIGHT - (SCREEN_HEIGHT - BUTTON_Y - table_height) / 2 )
        # create the result table for the current game statistics,
        # marking the shithead of the last game with red.
        self.result_table = ResultTable(upper_left, stats, shithead)
        # create a sprite list for the 'NEXT GAME' and 'EXIT GAME' buttons.
        self.button_list = arcade.SpriteList()
        # create the 'NEXT GAME' button.
        self.setup_next_button()
        # create the 'EXIT GAME' button.
        self.setup_exit_button()

    def on_mouse_press(self, x, y, button, key_modifiers):
        """
        Mouse button pressed event callback function.

        This function is called when the mouse button was pressed.
        We check if the mouse was clicked on the 'NEXT GAME' or 'EXIT GAME'
        button and change the button image to reflecting the pressed state.
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
            if button[0] == self.next:
                # clicked the 'NEXT GAME' button
                self.next.texture = arcade.load_texture(BUTTON_PRESSED)
                self.state = NEXT_STATE
            else:
                # clicked the 'EXIT GAME' button
                self.exit.texture = arcade.load_texture(BUTTON_PRESSED)
                self.state = EXIT_STATE
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
        # load the released button image into both button sprites
        self.next.texture = arcade.load_texture(BUTTON_RELEASED)
        self.exit.texture = arcade.load_texture(BUTTON_RELEASED)
        # execute the action of the pressed button
        if self.state == NEXT_STATE:
            # create, setup a game view with the current configuration,
            # and activate it (via config to avoid circular init)
            config.start_game(self.config, self.window)
        elif self.state == EXIT_STATE:
            sys.exit()
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
        self.result_table.draw()
        self.button_list.draw()
        self.next_text.draw()
        self.exit_text.draw()


def main():
    # test creating the title line specification
    title_specs = zip(TITLE_WIDTHS, TITLE_ALIGNS, TITLE_TEXTS)
    for spec in title_specs:
        print(spec)

    # getting the statistics for result table testing
    stats = Statistics()
    stats.load('ai_test_stats.json')
    stats.print()

    # testing the actual result view
    # open a window with predefined size and title
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    # create a ResultView
    result_view = ResultView()
    # and make it the view shown in the window
    window.show_view(result_view)
    # setup the result view for the current statistics and the last shithead
    config = {}     # dummy config
    result_view.setup(stats, 'Player1', config)

    # start
    arcade.run()

if __name__ == "__main__":
    main()