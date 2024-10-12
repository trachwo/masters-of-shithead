"""
Configuration screen of shithead game.

Arcade view called when pressing the 'Continue' button in the start view
(title screen).
It presents a number of input fields for game configuration.
On top is the input field for the configuration file. After start up it should
contain the name of the newest configuration file found in the game directory.
Pressing the 'LOAD' button next to it, will load all the configuration
parameters and also the player statistic counters from this file. To start a
new game from scratch just enter a new config file name.
The middle section contains the player configuration. We can setup games for 2
to 6 players, with Player0 always the human player. For Player1..Player5 we can
select one of the available AI types by clicking on the 'Type' field.
Player2..Player5 can be deactivated by leaving their 'Type' field empty.
Player names can be changed by clicking on the 'Name' fields.
Note, that the statistic counters for each player are also stored in the config
file and updated after each single game.
Pressing the 'START' button next to the player configuration starts the game
and saves the current configuration to the specified config file.
Some miscellaneous config parameters can be set in the bottom section.
With 'FastPlay' set to 'Yes', the AI players will not wait for the human player
to click the mouse after each of their plays before continuing.
With the 'LogLevel' we select the format of the output printed to console and
written to the log file.
'LogFile' selects if the console output shall also be written to a log file and
'FileName' specifies the name of this log file.

12.02.2023 Wolfgang Trachsler
"""

import json
import glob
import os

import arcade

# local imports (modules in same package)
from . import gui

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Sh*thead"

CONFIG_FILE_MAGIC = 47908652    # random number to identify config files
MAX_NOF_PLAYERS = 6
DEFAULT_FONT_SIZE = 14
TOP_MARGIN = 60

HSPACING = 20   # horizontal distance between labels/fields
HMARGIN = 20    # left and right margin (from background edges)
VSPACING = 50   # vertical distance between configuration entries
VMARGIN = 20    # top and bottonm margin (from background edges)

# dimensions of one player config entry
PLAYER_HEIGHT = 30  # height of one player entry
PLAYER_LABEL = 80   # width of 'Player0, Player1, ...' labels
PLAYER_TYPE = 150   # width of type field
PLAYER_NAME = 200   # width of name field

# dimensions of configuration background for 6 players + column headers
PLAYERS_WIDTH = (HMARGIN + PLAYER_LABEL + HSPACING + PLAYER_TYPE + HSPACING
                 + PLAYER_NAME + HMARGIN)
PLAYERS_HEIGHT = VMARGIN + PLAYER_HEIGHT + 6 * VSPACING + VMARGIN

# dimensions of configuration file entry
FILE_LABEL = 100    # width of 'ConfigFile' label
FILE_HEIGHT = 30    # height of configuration file entry
FILE_NAME = 300     # width of filename field

# dimensions of configuration file entry background
FILE_BG_WIDTH = PLAYERS_WIDTH
FILE_BG_HEIGHT = VMARGIN + FILE_HEIGHT + VMARGIN

# dimensions of buttons
BUTTON_SCALE = 0.7
BUTTON_WIDTH = 133      # with BUTTON_SCALE

# fast play selection dimensions
FAST_PLAY_LABEL = 80
FAST_PLAY = 50
FAST_PLAY_HEIGHT = 30

# card speed selection dimensions
CARD_SPEED_LABEL = 100
CARD_SPEED = 45
CARD_SPEED_HEIGHT = 30
CARD_SPEEDS = ['20', '30', '40', '50', '10']

# log level selection dimensions
LOG_LEVEL_LABEL = 80
LOG_LEVEL = 170
LOG_LEVEL_HEIGHT = 30
LOG_LEVELS = ['One Line', 'Game Display', 'Perfect Memory', 'No Secrets',
              'Debugging']

# log file selection/name dimensions
LOG_TO_FILE_LABEL = 80
LOG_TO_FILE = 50
LOG_TO_FILE_HEIGHT = 30
LOG_FILE_LABEL = 80
LOG_FILE_NAME = 170
LOG_FILE_NAME_HEIGHT = 30

# dimensions of miscellanous configs background
MISC_BG_WIDTH = PLAYERS_WIDTH
MISC_BG_HEIGHT = VMARGIN + FAST_PLAY_HEIGHT + 2 * VSPACING + VMARGIN

# calculate the left/right screen margin if we have the 'LOAD' button next to
# the config file entry
LEFT_MARGIN = (SCREEN_WIDTH - (PLAYERS_WIDTH + HSPACING + BUTTON_WIDTH)) / 2

MAX_NAME_LENGTH = 15
MAX_FILE_NAME_LENGTH = 18
MAX_LOG_FILE_NAME_LENGTH = 10

# default filename of configuration file
CONFIG_FILE = 'config.json'

# images used for buttons
BUTTON_RELEASED = ":resources:gui_basic_assets/red_button_normal.png"
BUTTON_PRESSED = ":resources:gui_basic_assets/red_button_press.png"

# coords of START button
START_X = 100
START_Y = 100

# coords of LOAD button
LOAD_X = 500
LOAD_Y = 100


def start_game(config, window, shithead=None):
    """
    Start the actual shithead game.
    Creates sets up the game view with the current configuration.
    Activates the game view in the arcade window.

    :param config:      config specified in the config view.
    :type config:       dict
    :param window:      arcade window created in main.
    :type window:       arcade.Window
    :param shithead:    shithead of the last round (None => 1st round)
    :type shithead:     str
    """
    # start the game with the current configuration
    game_view = gui.GameView(config)
    # setup the new game
    game_view.setup(shithead)
    # and switch to the new game view
    window.show_view(game_view)


class InputField(arcade.SpriteSolidColor):
    """
    Class representing an input field on the configuration screen.

    Input fields are are sprites with an associated text content.
    Clicking on an input field, sets the focus on this field. Depending on the
    InputField sub-class, we can either click on the field with the focus to
    step through several options, or use the keyboard to enter text into the
    field with the focus.
    """

    def __init__(self, pos, width, height):
        """
        Initialize the input field.

        :param pos:     coords of input field center.
        :type pos:      tuple of floats
        :param width:   width of input field.
        :type width:    int
        :param height:  height of input field.
        :type height:   int
        """
        super().__init__(width, height, arcade.csscolor.WHITE)
        self.position = pos     # place field at specified position
        self.txt = None

    def add_content(self, content, align='left'):
        """
        Create a text object as content of this input field.

        :param content:     content of input field.
        :type content:      str
        :param align:       text alignment ('left', 'center', 'right')
        :type align:        str
        """
        x, y = self.position  # get coords of input field center
        if align == 'left':
            self.txt = arcade.Text(
                content,
                x - self.width / 2 + 10, y,
                arcade.color.BLACK, DEFAULT_FONT_SIZE,
                anchor_x='left', anchor_y='center')
        elif align == 'right':
            self.txt = arcade.Text(
                content,
                x + self.width / 2 - 10, y,
                arcade.color.BLACK, DEFAULT_FONT_SIZE,
                anchor_x='right', anchor_y='center')
        else:
            self.txt = arcade.Text(
                content,
                x, y,
                arcade.color.BLACK, DEFAULT_FONT_SIZE,
                anchor_x='center', anchor_y='center')

    def execute_field_action(self, key, modifiers):
        """
        Action executed when field is in focus.
        """
        raise NotImplementedError("This method must be implemented in the"
                                  " subclass")

    def draw_field(self):
        """
        Render input field and its content on the screen.
        """
        super().draw()      # render input field sprite
        self.txt.draw()     # render text object


class OptionField(InputField):
    """
    Class representing the input field for option selection.

    Option fields allow the player to select one of serveral options from a
    list by clicking on the field.
    """

    def __init__(self, pos, width, height, options):
        """
        Initialize the option input field.

        :param pos:     coords of input field center.
        :type pos:      tuple of floats
        :param width:   width of input field.
        :type width:    int
        :param height:  height of input field.
        :type height:   int
        :param options: available options.
        :type options:  list of str.
        """
        super().__init__(pos, width, height)
        self.options = options
        self.sel = 0   # 1st option in list is the default option
        self.add_content(options[0])  # create field content

    def execute_field_action(self, key, modifiers):
        """
        Option field action.

        If this field is in focus, each further mouse click steps through the
        availbe options.
        """
        self.sel = (self.sel + 1) % len(self.options)
        # create the selected option as new field content
        self.add_content(self.options[self.sel])


class TextField(InputField):
    """
    Class representing the input field for text from keyboard.
    """

    def __init__(self, pos, width, height, max_len, text, align='left'):
        """
        Initialize the text input field.

        :param pos:     coords of input field center.
        :type pos:      tuple of floats
        :param width:   width of input field.
        :type width:    int
        :param height:  height of input field.
        :type height:   int
        :param max_len: maximum length of text
        :type max_len:  int
        :param text:    default text
        :type text:     str
        :param align:   text alignment ('left', 'center', 'right')
        :type align:    str
        """
        super().__init__(pos, width, height)
        if len(text) > max_len:
            # text too long => truncate
            self.text = text[:max_len]
        else:
            self.text = text
        self.max_len = max_len
        self.align = align
        self.focus = False              # True => started entering name
        self.previous = None            # backup of previous text
        self.add_content(text, align)   # create field content text object

    def execute_field_action(self, key, modifiers):
        """
        Enter text with keyboard into the field.

        The first key press with focus on this field will reset the text to an
        empty string. Printable characters will be added to the text, with the
        SHIFT modifier used to dicern between lowercase and uppercase.
        The BACKSPACE will remove the last char from the text.
        RETURN terminates text entry. If the text is empty when pressing
        return, the previous text will be restored. The focus flag will be
        reset, i.e. the next time we press a key with the focus on this field,
        text entry starts with resetting the text.

        :param key:             key pressed.
        :type key:              int
        :param key_modifiers:   SHIFT, CTRL, etc. pressed.
        :type key_modifiers:    int
        """
        if not self.focus:
            # 1st key pressed while in focus => reset text to empty string
            self.previous = self.text   # backup of previous text
            self.text = ''
            self.add_content(self.text, self.align)
            self.focus = True   # text entry started
        if key >= arcade.key.SPACE and key <= arcade.key.ASCIITILDE:
            # printable character entered
            if key >= arcade.key.A and key <= arcade.key.Z:
                if modifiers & arcade.key.MOD_SHIFT:
                    key -= 32   # ASCII of uppercase letter
            # add char to text
            if len(self.text) < self.max_len:
                self.text += chr(key)
                # create new content text object
                self.add_content(self.text, self.align)
        elif key == arcade.key.BACKSPACE:
            if len(self.text) > 0:
                # remove the last character
                self.text = self.text[:-1]
                # create new content text object
                self.add_content(self.text, self.align)
        elif key == arcade.key.RETURN:
            # terminate text entry
            if len(self.text) == 0:
                # empty text field => restore previous text
                self.text = self.previous
                # create new content text object
                self.add_content(self.text, self.align)
            # reset focus flag
            self.focus = False


class PlayerConfig():
    """
    Class for entering type and name of a player on the config screen.
    """

    def create_label(self, pos, index):
        """
        Creates label for player config as text object.

        Creates 'Player0, 'Player1' ... 'Player5' text object.

        :param pos:     x,y-coords of left/center of label.
        :type pos:      tuple
        :param index:   player index (0, 1, ..., 5)
        :type index:    int
        :return:        label text object.
        :rtype:         arcade.Text.
        """
        x, y = pos   # get coords of left/center of label
        # create the config label (Player0, Player1, ...)
        label = arcade.Text(
            f'Player{index}:',
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')
        return label

    def __init__(self, coords, index, types):
        """
        Player config Initializer.

        Creates the player label ('Player0, Player1, ..), and 2 input fields
        for the player type and the player name with their current content.

        :param coords:  X/Y-coors of player config (left/center)
        :type coords:   tuple of float
        :param index:   index of player in player list.
        :type index:    int
        :param types:   player types available for this player.
        :type types:    list
        """
        x, y = coords

        # create the config label (Player0, Player1, ...)
        self.label = self.create_label(coords, index)

        # create the player type input field
        x += PLAYER_LABEL + HSPACING + PLAYER_TYPE / 2
        self.type_field = OptionField((x, y), PLAYER_TYPE,
                                      PLAYER_HEIGHT, types)

        # create the player name input field
        x += PLAYER_TYPE / 2 + HSPACING + PLAYER_NAME / 2
        self.name_field = TextField((x, y), PLAYER_NAME,
                                    PLAYER_HEIGHT, MAX_NAME_LENGTH,
                                    f'Player{index}')

        # init statistic counters (shitheads, score, games, turns)
        # Note: the player statistics are stored in the config file
        self.counters = [0, 0, 0, 0]

    def draw(self):
        """
        Draw the label and both input fields with their content to the screen.
        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        self.label.draw()
        self.type_field.draw_field()
        self.name_field.draw()

    def get_config(self):
        """
        Get name, type and statistic counters for this player.

        Used to get the configuration parameters from the input fields when the
        game is started.

        :return:        player name, player type, player counters.
        :rtype:         tuple
        """
        name = self.name_field.text
        ptype = self.type_field.options[self.type_field.sel]
        return (name, ptype, self.counters)

    def set_config(self, config):
        """
        Set name, type and statistic counters for this player.

        Used to set the config fields after loading a configuration file.
        We first check if the specified configuration is valid, i.e. name is a
        non-empty string, type is in the options list of this player, and
        counters is a list of 4 integers.
        If this is not the case, we do nothing, i.e. keep the current
        configuration.

        :param config:  player name, player type, player counters.
        :type config:   tuple
        """
        # unpack list of player attributs
        name, ptype, counters = config

        # player name must be a non-empty string
        if not isinstance(name, str) or len(name) == 0:
            print(f"### Warning: player name must be a string,"
                  f" {self.name_field.text} not changed!")
            return

        if len(name) > MAX_NAME_LENGTH:
            print(f"### Warning: name length must be < {MAX_NAME_LENGTH}!")
            name = name[:MAX_NAME_LENGTH]

        # player statistic counters must be a list of 4 integers
        if not isinstance(counters, list) or len(counters) != 4:
            print(f"### Warning: player counters must be a list of 4 integers,"
                  f" {self.name_field.text} not changed!")
            return
        for counter in counters:
            if not isinstance(counter, int):
                print(f"### Warning: player counters must be a list of 4"
                      f" integers, {self.name_field.text} not changed!")
                return

        # type must be one of the types in the options list.
        try:
            sel = self.type_field.options.index(ptype)
        except ValueError as err:
            print(err)
            print(f"### Warning: player type must be one of the available"
                  f" types, {self.name_field.text} not changed!")
            return

        # everything ok => change this players configuration
        self.name_field.text = name
        self.name_field.add_content(name)
        self.type_field.sel = sel
        self.type_field.add_content(type)
        self.counters = counters
        return


class ConfigFile():
    '''
    Class for entering the name of a configuration file.
    '''

    def __init__(self, coords, filename):
        """
        Configuration File Initializer.

        Creates the configuration file input field.

        :param coords:      X/Y-coors of file config (left/center)
        :type coords:       tuple of float
        :param filename:    name of config file (incl. '.json')
        """
        x, y = coords
        filename = filename[:-5]  # remove '.json' from end of string

        # create the config file label.
        self.label = arcade.Text(
            'ConfigFile:',
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

        # create the config file input field
        x += FILE_LABEL + HSPACING + FILE_NAME / 2
        self.name_field = TextField((x, y), FILE_NAME,
                                    FILE_HEIGHT, MAX_FILE_NAME_LENGTH,
                                    filename, 'right')

        # create the extension
        self.extension = arcade.Text(
            '.json',
            x + FILE_NAME / 2,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

    def draw(self):
        """
        Draw label and filename input field with its content to the screen.
        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        self.label.draw()
        self.name_field.draw_field()
        self.extension.draw()

    def get_config(self):
        """
        Returns the name of the configuration file.

        :return:    filename of configuration file.
        :rtype:     str
        """
        # add extension 'json' to name in input field
        return self.name_field.text + '.json'


class FastPlayConfig():
    '''
    Class for selecting fast play.
    '''

    def __init__(self, coords):
        """
        Fast play configuration initializer.

        Creates the fast play selection field.

        :param coords:  X/Y-coors of fast play config (left/center)
        :type coords:   tuple of float
        """
        x, y = coords

        # create the FastPlay label
        self.label = arcade.Text(
            'FastPlay:',
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

        # create the fast play input field (with default 'Yes')
        x += FAST_PLAY_LABEL + HSPACING + FAST_PLAY / 2
        self.is_fast_play = OptionField((x, y), FAST_PLAY, FAST_PLAY_HEIGHT,
                                        ['Yes', 'No'])

    def draw(self):
        """
        Draw the label and the fast play selection field with its content to
        the screen.
        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        self.label.draw()
        self.is_fast_play.draw_field()

    def get_config(self):
        """
        Returns the fast play selection.

        :return:    fast play selection.
        :rtype:     bool
        """
        if self.is_fast_play.options[self.is_fast_play.sel] == 'Yes':
            return True
        else:
            return False

    def set_config(self, fast_play):
        '''
        Sets fast play selection.

        :param fast_play:   True => select 'Yes', False => select 'No'.
        :type fast_play:    bool
        '''
        # fast_play must be a boolean
        if not isinstance(fast_play, bool):
            # print warning, keep previous value
            print("### Warning: fast play must be 'True' or 'False'!")
            return

        # everything ok
        if fast_play:
            self.is_fast_play.sel = 0
            self.is_fast_play.add_content('Yes')
        else:
            self.is_fast_play.sel = 1
            self.is_fast_play.add_content('No')


class CardSpeedConfig():
    '''
    Class for card animation speed selection.
    '''

    def __init__(self, coords):
        """
        Card speed selection initializer.

        Creates the card speed selection field.

        :param coords:  X/Y-coors of log level config (left/center)
        :type coords:   tuple of float
        """
        x, y = coords

        # create the card speed label
        self.label = arcade.Text(
            'CardSpeed:',
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

        # create the card speed input field
        x += CARD_SPEED_LABEL + HSPACING + CARD_SPEED / 2
        self.speed = OptionField((x, y), CARD_SPEED, CARD_SPEED_HEIGHT,
                                 CARD_SPEEDS)

    def draw(self):
        """
        Draw the label and the card speed selection field with its content to
        the screen.
        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        self.label.draw()
        self.speed.draw_field()

    def get_config(self):
        """
        Gets the selected card speed from the input field.

        :return:    card speed.
        :rtype:     str
        """
        return self.speed.options[self.speed.sel]

    def set_config(self, card_speed):
        '''
        Sets card speed selection in input field.

        Used to set the card speed read from the config-file. Since the
        config-file can be edited, we have to check if the read value is valid.
        If the card speed is not valid, we issue a warning and keep the default
        value.

        :param card_speed:  '10', '20', '30', '40', or '50'.
        :type log_level:    str
        '''
        # card speed must be a non-empty string
        if not isinstance(card_speed, str) or len(card_speed) == 0:
            # print warning, keep previous value
            print('### Warning: card speed must be a non-empty string!')
            return

        # card speed must be one of the strings in the options list.
        try:
            sel = self.speed.options.index(card_speed)
        except ValueError as err:
            print(err)
            print(f"### Warning: {card_speed} is not a valid"
                  f" card speed string!")
            return

        # set index of specified card speed in card speed list as selection
        self.speed.sel = sel
        self.speed.add_content(card_speed)


class LogLevelConfig():
    '''
    Class for log level selection.
    '''

    def __init__(self, coords):
        """
        Log level selection initializer.

        Creates the log level selection field.

        :param coords:  X/Y-coors of log level config (left/center)
        :type coords:   tuple of float
        """
        x, y = coords

        # create the Log level label
        self.label = arcade.Text(
            'LogLevel:',
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

        # create the log level input field
        x += LOG_LEVEL_LABEL + HSPACING + LOG_LEVEL / 2
        self.level = OptionField((x, y), LOG_LEVEL, LOG_LEVEL_HEIGHT,
                                 LOG_LEVELS)

    def draw(self):
        """
        Draw the label and the log level selection field with its content to
        the screen.
        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        self.label.draw()
        self.level.draw_field()

    def get_config(self):
        """
        Gets the selected log level from the input field.

        :return:    log level.
        :rtype:     str
        """
        return self.level.options[self.level.sel]

    def set_config(self, log_level):
        '''
        Sets log-level selection in input field.

        Used to set the log-level read from the config-file. Since the
        config-file can be edited, we have to check if the read value is valid.
        If the log-level is not valid, we issue a warning and keep the default
        value.

        :param log_level:   'One Line', 'Game Display', 'Perfect Memory',
                            'No Secrets', or 'Debugging'.
        :type log_level:    str
        '''
        # log_level must be a non-empty string
        if not isinstance(log_level, str) or len(log_level) == 0:
            # print warning, keep previous value
            print('### Warning: log-level  must be a non-empty string!')
            return

        # log_level must be one of the strings in the options list.
        try:
            sel = self.level.options.index(log_level)
        except ValueError as err:
            print(err)
            print(f"### Warning: {log_level} is not a valid log-level string!")
            return

        # set index of specified log_level in log-level list as selection
        self.level.sel = sel
        self.level.add_content(log_level)


class LogFileConfig():
    '''
    Class for log file activation and filename entering.
    '''

    def __init__(self, coords):
        """
        Log file initializer.

        Creates the log file selection and input field.

        :param coords:  X/Y-coors of log level selection (left/center)
        :type coords:   tuple of float
        """
        x, y = coords

        # create the Log file selection label
        self.to_file_label = arcade.Text(
            'LogFile:',
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

        # create the log to file selection field (with default 'Dbg')
        x += LOG_TO_FILE_LABEL + HSPACING + LOG_TO_FILE / 2
        self.log_to_file = OptionField((x, y), LOG_TO_FILE, LOG_TO_FILE_HEIGHT,
                                       ['Dbg', 'No', 'Yes'])

        # create the log file label.
        x += LOG_TO_FILE / 2 + HSPACING
        self.log_file_label = arcade.Text(
            'FileName:',
            x, y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

        # create the log file input field
        x += LOG_FILE_LABEL + HSPACING + LOG_FILE_NAME / 2
        self.name_field = TextField((x, y), LOG_FILE_NAME,
                                    LOG_FILE_NAME_HEIGHT,
                                    MAX_LOG_FILE_NAME_LENGTH,
                                    'shitlog', 'right')

        # create the extension
        self.extension = arcade.Text(
            '.log',
            x + LOG_FILE_NAME / 2, y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='left',
            anchor_y='center')

    def draw(self):
        """
        Draw the label and the log to file selection field with its content to
        the screen.
        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        self.to_file_label.draw()
        self.log_to_file.draw_field()
        self.log_file_label.draw()
        self.name_field.draw_field()
        self.extension.draw()

    def get_config(self):
        """
        Returns the log to file selection and the log file name.

        There are options:
            - 'No' => don't log to file
            - 'Yes' => log to file with the selected log-level
            - 'Dbg' => log to file with log-level = 'Debugging'
        This allows us to log the unwieldy debugging info to a file,
        while seeing oneline log-messages in the console.

        :return:    log to file, debug , log file name.
        :rtype:     tuple
        """
        if self.log_to_file.options[self.log_to_file.sel] == 'Yes':
            return (True, False, self.name_field.text + '.log')
        elif self.log_to_file.options[self.log_to_file.sel] == 'Dbg':
            return (True, True, self.name_field.text + '.log')
        else:
            return (False, False,  None)

    def set_config(self, log_file):
        '''
        Sets the log-file config in the input field.

        Used to set the log-file information read from the config-file in the
        input fields. Since the config-file is editable, we have to check if
        the read information is valid. If it's not valid, we issue a warning
        and keep the defaults.

        :param log_file:  'log-to-file' flag, 'debugging' flag, log-file-name.
        :type log_level:  tuple of bool, bool, and str.
        '''
        # the 'log-to-file' flag must be a boolean
        if not isinstance(log_file[0], bool):
            # print warning, keep previous value
            print("### Warning: log-to-file flag  must be 'True' or 'False'!")
            return

        # the 'debugging' flag must be a boolean
        if not isinstance(log_file[1], bool):
            # print warning, keep previous value
            print("### Warning: debugging flag  must be 'True' or 'False'!")
            return

        # the log-file-name must be a string ending with the extension '.log'
        if (log_file[0] and (not isinstance(log_file[2], str)
                             or log_file[2][-4:] != '.log')):
            print("### Warning: log-file-name must be a string ending on"
                  " '.log'!")
            return
        if log_file[0] and len(log_file[2]) > MAX_LOG_FILE_NAME_LENGTH + 4:
            print(f"### Warning: log-file-name length"
                  f" must be < {MAX_LOG_FILE_NAME_LENGTH + 4}!")
            log_file[2] = log_file[2][:MAX_LOG_FILE_NAME_LENGTH] + '.log'
            return

        # everything ok => set log-to-file selection to 'Yes', 'Dbg', or 'No'
        if log_file[0]:
            if log_file[1]:
                self.log_to_file.sel = 0
                self.log_to_file.add_content('Dbg')
            else:
                self.log_to_file.sel = 2
                self.log_to_file.add_content('Yes')
            # set the log-file-name without the extension
            self.name_field.text = log_file[2][:-4]
            self.name_field.add_content(log_file[2][:-4], 'right')
        else:
            self.log_to_file.sel = 1
            self.log_to_file.add_content('No')
            # set empty log-file-name without the extension
            self.name_field.text = 'shitlog'
            self.name_field.add_content('shitlog', 'right')


class ConfigView(arcade.View):
    '''
    View where we show the configuration options.
    '''

    def __init__(self):
        """
        Configuration view initializer.
        """
        # Initializes the super class
        super().__init__()

        self.file_config = None     # configuration file
        self.players = None         # list of players
        self.stats = None           # game statistics
        self.fields = None          # sprite list of input fields
        self.buttons = None         # sprite list of buttons
        self.focus = None           # input field we last clicked on
        self.start = None           # start button
        self.start_text = None      # start button text
        self.load = None            # load button
        self.file_config_bg = None  # file config background color
        self.load_text = None       # load button text
        self.players_config_bg = None   # player config background color
        self.type_header = None     # player config type column header
        self.name_header = None     # player config name column header
        self.misc_bg = None         # miscelaneous config background color
        self.fast_play = None       # fast play config
        self.card_speed = None      # card speed config
        self.log_level = None       # log level config
        self.log_file = None        # log file config

        # set the background color to amazon green.
        arcade.set_background_color(arcade.color.AMAZON)

    def create_header(self, pos, header):
        """
        Creates a column header above the players configuration .

        :param pos:     position of player config field (x/y-center).
        :type pos:      tuple
        :param header:  header string
        :type header:   str
        :return:        header text object.
        :rtype:         arcade.Text.
        """
        x, y = pos  # get coords of the field below the header
        header_text = arcade.Text(
            header,
            x,
            y + VSPACING,           # above the field
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')
        return header_text

    def setup_button(self, x, y, label):
        """
        Creates button button sprite and label text object.

        Creates a button sprite.
        Adds the created button sprite to the sprite list.
        Creates the label text object.
        """
        button = arcade.Sprite(BUTTON_RELEASED, BUTTON_SCALE,
                               hit_box_algorithm='None')
        button.position = (x, y)
        # add button to the buttons sprite list (=> on_mouse_press)
        self.buttons.append(button)

        # create button label
        button_label = arcade.Text(
            label,
            x,
            y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')

        return (button, button_label)

    def find_newest_config(self):
        """
        Find the newest '.json' file containing a shithead configuration.

        We first make a list of files with extension 'json' and sort it
        ascending by modification time. Then we go through the list and try to
        load each of the files as json file and check if it contains the magic
        number. The first such file found is returned.
        TODO only if json file is not empty

        :return:    name of newest config file
                    or default if no config file found.
        :rtype:     str
        """
        files = glob.glob('*.json')
        sorted_asc = sorted(files, key=lambda t: -os.stat(t).st_mtime)
        for filename in sorted_asc:
            try:
                with open(filename, 'r', encoding='utf-8') as json_file:
                    config = json.load(json_file)
            except IOError as err:
                print(err)
                continue
            if (isinstance(config, dict) and 'magic' in config.keys() and
                    config['magic'] == CONFIG_FILE_MAGIC):
                return filename
        # no config file found => return default filename
        return CONFIG_FILE

    def setup_config_file_config(self):
        """
        Setup the ConfigFile configuration.

        Creates the text input field for the configuration file
        and the 'LOAD' button which triggers loading the configuration from
        the specified file.
        """
        # create a dark green background for the config file input field
        self.file_config_bg = arcade.SpriteSolidColor(
            FILE_BG_WIDTH, FILE_BG_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)

        # we place it (center/center) at the top of the configuration view
        x = LEFT_MARGIN + FILE_BG_WIDTH / 2
        y = SCREEN_HEIGHT - TOP_MARGIN - FILE_BG_HEIGHT / 2
        self.file_config_bg.position = (x, y)

        # search newest config file
        filename = self.find_newest_config()
        # coords of ConfigFile (left/center)
        x = LEFT_MARGIN + HMARGIN
        # create the config filename input field.
        self.file_config = ConfigFile((x, y), filename)
        # add the filename input field to the sprite list
        self.fields.append(self.file_config.name_field)

        # create the load button next to ConfigFile (center, center)
        x = LEFT_MARGIN + FILE_BG_WIDTH + HSPACING + BUTTON_WIDTH / 2
        self.load, self.load_text = self.setup_button(x, y, 'LOAD')

    def setup_player_config(self):
        """
        Setup the player configuration.

        Creates the input fields for 6 players, where we can select the player
        type and the name of the player.
        Player0 is always the human player.
        Player1 must always be selected (we need at least 2 players.)
        Player2..Player5 are AI players which can be left empty.
        The 'START' button is setup next to the player configuration.
        """
        # create a dark green background for the players configuration
        self.players_config_bg = arcade.SpriteSolidColor(
            PLAYERS_WIDTH, PLAYERS_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)

        # we place it (center, center) below ConfigFile
        x = LEFT_MARGIN + PLAYERS_WIDTH / 2
        y = (SCREEN_HEIGHT - TOP_MARGIN - FILE_BG_HEIGHT - VSPACING / 2
             - PLAYERS_HEIGHT / 2)
        self.players_config_bg.position = (x, y)

        # coords of Player0 (left/center)
        x = LEFT_MARGIN + HMARGIN
        y = (SCREEN_HEIGHT - TOP_MARGIN - FILE_BG_HEIGHT - VSPACING / 2
             - 1.5 * VSPACING)   # leave room for column headers

        # create the player config fields
        self.players = []
        for i in range(MAX_NOF_PLAYERS):
            if i == 0:
                # Player0 is always the human player
                types = ['Human']
            elif i == 1:
                # Player1 must be one of the AI players
                types = ['ShitHappens', 'CheapShit', 'TakeShit', 'DeepShit',
                         'BullShit']
            else:
                # Player2..Player5 are AI players or empty
                types = ['---', 'ShitHappens', 'CheapShit', 'TakeShit',
                         'DeepShit', 'BullShit']
            player = PlayerConfig((x, y), i, types)
            # add to player config list
            self.players.append(player)
            # and player's entry fields to the sprite list
            self.fields.append(player.type_field)
            self.fields.append(player.name_field)
            y -= VSPACING

        # create the type column header above Player0's type field.
        pos = self.players[0].type_field.position
        self.type_header = self.create_header(pos, 'Type')

        # create the name column header above Player0's name field.
        pos = self.players[0].name_field.position
        self.name_header = self.create_header(pos, 'Name')

        # create the start button next to the players configuration
        # (center, center)
        x = LEFT_MARGIN + PLAYERS_WIDTH + HSPACING + BUTTON_WIDTH / 2
        y = (SCREEN_HEIGHT - TOP_MARGIN - FILE_BG_HEIGHT - VSPACING / 2
             - PLAYERS_HEIGHT / 2)
        self.start, self.start_text = self.setup_button(x, y, 'START')

    def setup_misc_config(self):
        """
        Setup miscelaneous configuration.

        Setup the input fields for selecting FastPlay, the LogLevel,
        the log-to-file selector, and the log-file-name.
        """
        # create a dark green background for miscellanious configurations
        self.misc_bg = arcade.SpriteSolidColor(
            MISC_BG_WIDTH, MISC_BG_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        # we place it (center/center) below the player configuration
        x = LEFT_MARGIN + MISC_BG_WIDTH / 2
        y = (SCREEN_HEIGHT - TOP_MARGIN - FILE_BG_HEIGHT - VSPACING / 2
             - PLAYERS_HEIGHT - VSPACING / 2 - MISC_BG_HEIGHT / 2)
        self.misc_bg.position = (x, y)

        # coords of FastPlayConfig (left/center)
        x = LEFT_MARGIN + HMARGIN
        y += MISC_BG_HEIGHT / 2 - VMARGIN - FAST_PLAY_HEIGHT / 2
        # create the fast play selection field
        self.fast_play = FastPlayConfig((x, y))
        self.fields.append(self.fast_play.is_fast_play)

        # coords of CardSpeedConfig (left/center)
        x += FAST_PLAY_LABEL + HSPACING + FAST_PLAY + HSPACING
        # create the card speed selection field
        self.card_speed = CardSpeedConfig((x, y))
        self.fields.append(self.card_speed.speed)

        # coords of LogLevelConfig (left/center)
        x = LEFT_MARGIN + HMARGIN
        y -= VSPACING
        # create the log level selection field
        self.log_level = LogLevelConfig((x, y))
        self.fields.append(self.log_level.level)

        # coords of LogFileConfig (left/center)
        y -= VSPACING
        # create the log file fields
        self.log_file = LogFileConfig((x, y))
        self.fields.append(self.log_file.log_to_file)
        self.fields.append(self.log_file.name_field)

    def setup(self):
        """
        Setup the configuration view.

        Creates the sprite lists for the input fields and buttons.
        Sets up the configuration file input fields and the 'LOAD' button.
        Sets up the player input fields and the 'START' button.
        Sets up the FastPlay selection and the logging input fields.
        """
        # create sprite lists for input fields and buttons
        self.fields = arcade.SpriteList()
        self.buttons = arcade.SpriteList()

        # create the config file input field and the 'LOAD' button
        self.setup_config_file_config()

        # creates the player input fields and the 'START' button
        self.setup_player_config()

        # create the input fields for FastPlay and Logging
        self.setup_misc_config()

    def get_config(self):
        """
        Get the configuration from the input fields.

        Reads the game parameters from the input fields.

        :return:    configuration.
        :rtype:     dict
        """
        config = {}     # configuration dictionary
        config['magic'] = CONFIG_FILE_MAGIC
        # name of config file
        config['config_file'] = self.file_config.get_config()
        players = []    # list of player configurations
        for player in self.players:
            players.append(player.get_config())
        config['players'] = players
        config['fast_play'] = self.fast_play.get_config()
        config['card_speed'] = self.card_speed.get_config()
        config['log_level'] = self.log_level.get_config()
        config['log_file'] = self.log_file.get_config()
        return config

    def save_config(self):
        '''
        Write configuration to json file.
        '''
        config = self.get_config()
        filename = config['config_file']
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(config, json_file, indent=4)

    def set_config(self, config):
        """
        Set the specified configuration in the input fields.

        Used to update the configuration input fields with the data read from
        the specified configuration file.

        :param config:  configuration (e.g. loaded from file)
        :type config:   dict
        """
        # the players config must be a list of 6 players.
        if (not isinstance(config['players'], list)
                or len(config['players']) != 6):
            print("### Warning: players must be a list of 6 player configs,"
                  " config not changed!")
            return
        # set for each player the name, type, and counters according to
        # the specified config
        for i, player in enumerate(self.players):
            player.set_config(config['players'][i])
        # set the fast play selection
        self.fast_play.set_config(config['fast_play'])
        # set the card speed selection
        self.card_speed.set_config(config['card_speed'])
        # set log-level selection
        self.log_level.set_config(config['log_level'])
        # set log_to_file selection and log-file-name.
        self.log_file.set_config(config['log_file'])

    def load_config(self):
        '''
        Loads configuration from json file.

        If file is not present, issues a warning and continues with default
        configuration.
        Updates the input fields with the data read from the json-file.
        '''
        # get filename from the ConfigFile input field.
        filename = self.file_config.get_config()
        try:
            with open(filename, 'r', encoding='utf-8') as json_file:
                config = json.load(json_file)
        except IOError as err:
            print(err)
            print(f"### Warning: couldn't load file {filename},"
                  " continue with current configuration")
            return

        # set the loaded configuration in the input fields
        self.set_config(config)

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Mouse button pressed event callback function.

        This function is called when the mouse button was pressed.
        If the mouse was pressed over one of the input fields and this field
        was not in focus before, we put it in focus, i.e. we draw a bright
        green frame around it. If it was already in focus we execute the
        corresponding field action, i.e. step through the options or enter
        text.
        If the mouse was pressed over the 'LOAD' button the specified
        configuration file is loaded.
        If the mouse was pressed over the 'START' button, the configuration is
        saved to the specified configuration file and the game view is called
        with the configuration extracted from the input fields.

        :param x:               X-coord of mouse when button was pressed.
        :type x:                float
        :param y:               Y-coord of mouse when button was pressed.
        :type y:                float
        :param button:          the mouse button which was pressed.
        :type button:           int
        :param modifiers:       Keyboard modifiers e.g. SHIFT, ALT, etc.
        :type modifiers:        int
        """

        # get list of field sprites we clicked on
        fields = arcade.get_sprites_at_point((x, y), self.fields)

        # have we clicked on an input field?
        if len(fields) > 0:
            if self.focus and self.focus == fields[0]:
                # the field we clicked on is already in focus
                if isinstance(self.focus, OptionField):
                    # option selection input field => execute its action
                    self.focus.execute_field_action(None, None)
            else:
                # put the clicked on field in focus
                self.focus = fields[0]
        else:
            # not clicked on an input field => out of focus
            self.focus = None

        # check if we have pressed one of the buttons
        button = arcade.get_sprites_at_point((x, y), self.buttons)
        if len(button) > 0:
            # mouse clicked on the buttons
            if button[0] == self.start:
                # clicked the 'START' button
                self.start.texture = arcade.load_texture(BUTTON_PRESSED)
                # save the current configuration to a JSON file
                # use 'config_file' entry as filename
                self.save_config()
                # setup game view with this config and activate it
                # => start the actual game
                start_game(self.get_config(), self.window)
            elif button[0] == self.load:
                # clicked the 'LOAD' button
                self.load.texture = arcade.load_texture(BUTTON_PRESSED)
                # load the configuration with the filenamein the ConfigFile
                # input field.
                self.load_config()

    def on_mouse_release(self, x, y, button, modifiers):
        """
        Mouse button released event callback function.

        This function is called when the mouse button was released.

        :param x:               X-coord of mouse when button was released.
        :type x:                float
        :param y:               Y-coord of mouse when button was released.
        :type y:                float
        :param button:          the mouse button which was released.
        :type button:           int
        :param modifiers:       key modifiers e.g. SHIFT, ALT, etc.
        :type modifiers:        int
        """
        # load the released button image into the button sprites
        self.start.texture = arcade.load_texture(BUTTON_RELEASED)
        self.load.texture = arcade.load_texture(BUTTON_RELEASED)

    def on_key_press(self, symbol, modifiers):
        """
        Method called when keyboard key is pressed.

        Enters text into a text input field which is in focus.

        :param symbol:          code of key pressed.
        :type symbol:           int
        :param modifiers:       SHIFT, CTRL, etc. pressed.
        :type modifiers:        int
        """
        if self.focus and isinstance(self.focus, TextField):
            # the focus is on a text input field
            # => execute the text input field action.
            self.focus.execute_field_action(symbol, modifiers)

            if symbol == arcade.key.RETURN:
                # text entry complete => go out of focus
                self.focus = None

    def draw_focus_frame(self):
        """
        Draw a bright green frame around the input field in focus.
        """
        if self.focus:
            arcade.draw_rectangle_outline(
                    self.focus.position[0],     # x-coord
                    self.focus.position[1],     # y-coord
                    self.focus.width+4,         # width
                    self.focus.height+4,        # height
                    arcade.color.BRIGHT_GREEN,  # color
                    3,                          # border size
                    0)                          # tilt angle

    def on_draw(self):
        """
        Render the screen callback function.

        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        # clear the screen
        self.clear()

        # call the draw method() of each config screen element.
        self.players_config_bg.draw()
        self.type_header.draw()
        self.name_header.draw()
        for player in self.players:
            player.draw()
        self.file_config_bg.draw()
        self.file_config.draw()
        self.start.draw()
        self.start_text.draw()
        self.load.draw()
        self.load_text.draw()
        self.misc_bg.draw()
        self.fast_play.draw()
        self.card_speed.draw()
        self.log_level.draw()
        self.log_file.draw()
        self.draw_focus_frame()


def main():
    """
    Test for configuration window.
    """

    # testing the config view
    # open a window with predefined size and title
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    # create a ConfigView
    config_view = ConfigView()
    # and make it the view shown in the window
    window.show_view(config_view)
    # setup the config view
    config_view.setup()

    # start
    arcade.run()


if __name__ == "__main__":
    main()
