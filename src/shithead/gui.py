"""
Graphics stuff for shithead game.

The gui module contains everything necessary to play the shithead game with
the gui:
    - CardSprite class:
      Sprite representing a card in the game view.
      If face up, an image referenced by suit and rank of the card is loaded.
      If face down a red or blue back is loaded, depending on the deck id
      (even or odd). Each CardSprite object keeps track of its screen location.

    - Message class:
      Draws up to 5 lines of text in the center of the game screen (above the
      talon):
        -- Turn count, direction, current player
        -- instructions
        -- tool tips

    - Place class:
      We use objects of the Place class to manage all the different piles of
      CardSprites on the screen. Each place has a name which is used as key in
      a dictionary to address this place ('removed', 'talon', 'discard', and
      player names e.g. 'Wolfi', 'Player1', etc.). Each place contains a list
      of coordinates and a list of corresponding card lists. 'removed',
      'talon', and 'discard' have only one entry in each of these lists, e.g.
      places['talon'].coords[0] = (TALON_X, TALON_Y) and
      places['talon'].cards[0] = [<card_sprite0>, <card_sprite1>, ...] but in
      case of the player places we have 4 entries, with the table cards at
      index 0..2 and the hand cards at index 3.
      In case of the players the Place object also contains a text object with
      the name of the player placed beneath his table cards, and one filled and
      one outlined rectangle around this text object to mark this player as
      current or next player.

    - CardMover class:
      A single card mover manages the locations and the movement of card
      sprites on the screen.
      During setup:
        -- creates dark green mats, where removed, talon, and discard pile
           cards are placed along the middle of the screen and adds them to the
           GameView mat sprite list.
        -- creates Place objects for each of these core mats and adds them to
           its places dictionary.
        -- creates 3 dark green mats for the human player's table cards below
           talon and discard pile (the hand cards are spread out in the area
           below them) and adds them to the GameView mat sprite list.
        -- creates a Place object with a list of 4 coordinates and a list of 4
           card sprite lists and adds it to its places list. The entries 0..2
           correspond to the 3 table card mats. The 4th entry gets the coords
           of an invisible mat below the center table card. The 4th entry is
           for the human player's hand cards, which are sorted by rank and
           spread out face up.
        -- creates 4 dark green mats (representing table and hand cards) per
           opponent player in the upper part of the screen and adds them to the
           GameView mat sprite list. Their position depends on the number of
           opponent players (1 - 5).
        -- creates a Place object with 4 coords and card list entries per
           opponent player and adds them to its places list.

      All card sprites start their life face down in the talon, i.e. they all
      get the coordinates of the talon as their position.
      Depending on the selected plays the card mover has to be programmed to
      move one or more cards to a new target place (e.g. at the start of the
      game a random number of 'burnt' cards is moved to the removed card pile).
      This is done by adding one entry per card sprite to the move list of the
      card mover.
      Move list entries have the format (card, name, idx, delay, face_up) with:
            - card      => card sprite to be moved.
            - name      => name of the target place.
                           ('talon', 'removed', 'discard', or player name).
            - idx       => index of target place's card list (0..3).
            - delay     => delay [s] after which card starts moving.
            - face_up   => place card face up at target if True.
      After all cards to be moved have been added to the Move list, we start
      the card mover and increment the card mover time with each GameView
      update() call (about 60 times per sec). Whenever the 'delay' parameter of
      a move list entry expires, the corresponding card sprite starts moving
      (dx>0,dy>0) with each update() call) towards its programmed target
      (e.g. places['removed'].coords[0]) and is removed from its source place
      (e.g. places['talon'].cards[0]). As soon as a moving card sprite is close
      enough to its target, it stops (dx=0,dy=0),gets the target coords as
      position, is added to the targets card list, and the corresponding entry
      is removed from the move list. As soon as the move list is empty, the
      'started' flag of the card mover will be reset to indicate, that the card
      mover has finished.

    - GameView class:
      This the arcade view where the actual shithead game is played.
      When we press the 'START' button in the configuration view, the game view
      will be created, setup with the selected configuration, and then made the
      active view in the arcade window.

      -- setup():
         --- creates the fup table and loads it from its json-file.
         --- creates the list of players (name, type) from the player
             configuration.
         --- creates the statistics and loads it with the counts found in the
             player configuration.
         --- creates a sprite list for the card sprites.
         --- creates a sprite list for the dark green mat sprites.
         --- creates a dictionary to map cards (suit, rank) to card sprites.
         --- creates the card mover.
         --- lets the card mover setup the core mats ('removed', 'talon',
             'discard') and their corresponding mover target places.
         --- lets the card mover setup the player mats and their corresponding
             mover target places.
         --- creates the 'DONE' button.
         --- creates the message window.
         --- creates the log-info from the configuraton.
         --- calculates the number of decks needed for this number of players.
         --- creates the initial game state
             => talon with necessary number of decks.
         --- applies the 'SHUFFLE' play to the initial game state
             => next game state with shuffled talon.
         --- creates for each card in the talon a card sprite with the
             coordinates of the talon as position and adds it to the card
             sprite list and the card list of the card mover's 'talon' place.
             Also enter each sprite into the card-to-sprite dictionary using
             the corresponding card as key.
         --- applies the 'BURN' play to the current game state to remove some
             cards from the talon. Program the card mover to move these cards
             to the removed cards pile.
         --- programs the card mover to move dealt cards from the talon to the
             players. We do this before changing the state, because we use the
             talon state to find the corresponding sprite. Then applies the
             'DEAL' play to the current state.
         --- starts the card mover to show burning and dealing of cards.

      -- on_draw():
         arcade callback called about 60 times per sec to redraw the game view.
         --- clears the screen.
         --- draws the dark green mats, where cards can be placed.
         --- draws the 'DONE' button.
         --- draws the number of cards in the removed cards pile, talon,
             discard pile, and in the the opponent players hands below the
             corresponding mat.
         --- draws the player names below their table cards.
         --- marks the legal plays of the human player with green frames.
         --- draws the lines of text in the message window.
         --- draws all card sprites (done last because they are on top of
             everything else).

      -- on_mouse_press():
         arcade callback called if one of the mouse buttons was pressed.
         --- checks if the human player has clicked on a card or button and if
             yes, maps the clicked on location to the corresponding play (e.g.
             clicked on talon => 'REFILL', clicked on 'DONE' button => 'END')
         --- in case of the 'DONE' button, replaces the 'released' button image
             with the 'pressed' button image.

      -- on_mouse_release():
         arcade callback called if the mouse button was released.
         --- replaces 'pressed' button image with 'released' button image.

      -- on_mouse_motion():
         arcade callback called if the mouse was moved.
         --- checks if the mouse is hovering over a card or button and if yes,
             displays a corresponding game rule hint in the message window.

      -- on_update():
         arcade callback called about 60 times per sec.
         this is where the actual game loop is implemented.
         --- waits till the card mover has finished moving cards.
         --- waits till any timeouts for the human player to catch on have
             expired.
         --- checks if the discard pile was killed by a '10' or taken with a
             face down table card
             => move discard pile to removed cards pile or player hand.
         --- waits for human player reaction ('click anywhere to continue').
         --- updates the message window according to the game phase.
         --- checks if the shithead has been found (only one player left)
             and if yes:
                ---- updates the statistic counters in the player configuration
                     and saves the configuration to disk.
                ---- prepares the result view with the newest statistics.
                ---- waits for prompt from the human player before switching
                     to the result view.
         --- get the next play of the current player and apply it to the
             current state in order to get to the next game state.

22.01.2023 Wolfgang Trachsler
"""

import math
import json

import arcade

# local imports (modules in same package)
from .player import HumanPlayer, AiPlayer
from .cards import Card, Deck
from .discard import Discard
from .fup_table import FupTable, FUP_TABLE_FILE
from . import player as plr  # to avoid confusion with 'player'
from .stats import Statistics
from .game import Game
from .state import (State, SWAPPING_CARDS, FIND_STARTER, PLAY_GAME,
                    SHITHEAD_FOUND, ABORTED)
from .state import STARTING_SUITS, STARTING_RANKS
from .play import Play
from . import result

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Sh*thead"

# face down image for up to 2 decks with id=0 or 1
# cards with id=0 have red backs
# cards with id=1 have blue backs
FACE_DOWN_IMAGE = [':resources:images/cards/cardBack_red2.png',
                   ':resources:images/cards/cardBack_blue2.png']

# Card size
CARD_SCALE = 0.5
CARD_WIDTH = int(140 * CARD_SCALE)
CARD_HEIGHT = int(190 * CARD_SCALE)

# horizontal gap between cards in percent of card width
HORIZONTAL_MARGIN_PERCENT = 0.10

# if we fan out cards stacked on each other, how far apart to fan them?
CARD_VERTICAL_OFFSET = CARD_HEIGHT * CARD_SCALE * 0.3
CARD_HORIZONTAL_OFFSET = CARD_WIDTH * CARD_SCALE * 0.5
# horizontal distance between 2 columns
X_SPACING = CARD_WIDTH + CARD_WIDTH * HORIZONTAL_MARGIN_PERCENT

# The absolut screen margins are defined by the full player hand display,
# i.e. 13 columns of cards.
MARGIN = int((SCREEN_WIDTH - (12 * X_SPACING + CARD_WIDTH)) / 2)

# Position of human players hand cards (center)
# with a maximum of 2 decks we should have vertical space for 8 cards
HAND_X = int(SCREEN_WIDTH / 2)
HAND_Y = 3 * CARD_VERTICAL_OFFSET + int(CARD_HEIGHT / 2) + MARGIN

Y_SPACING = int((SCREEN_HEIGHT - HAND_Y - MARGIN - CARD_HEIGHT / 2) / 4)

# Position of talon (middle of the screen)
TALON_X = int(SCREEN_WIDTH / 2)
TALON_Y = int(HAND_Y + 2 * Y_SPACING)

# Position of discard pile
DISCARD_X = TALON_X + X_SPACING
DISCARD_Y = TALON_Y

# Position of removed card pile on the left side
REMOVED_X = MARGIN + int(CARD_WIDTH / 2)
REMOVED_Y = TALON_Y

# Position of players table cards
TABLE_X = TALON_X - X_SPACING
TABLE_Y = HAND_Y + Y_SPACING

# Position of 'End Turn' Button
BUTTON_X = SCREEN_WIDTH - MARGIN - (CARD_WIDTH + 3 * X_SPACING) / 2
BUTTON_Y = TABLE_Y
BUTTON_SCALE = 0.7
BUTTON_RELEASED = ":resources:gui_basic_assets/red_button_normal.png"
BUTTON_PRESSED = ":resources:gui_basic_assets/red_button_press.png"

# Opponent area (hand + table cards => 4 stacks)
OPPONENT_WIDTH = 3 * X_SPACING + CARD_WIDTH
OPPONENT_HEIGHT = CARD_HEIGHT

# Upper row of opponent cards (10-, 11-, 12-, 1-, 2-o'clock)
OPP_UPPER_Y = HAND_Y + 4 * Y_SPACING

# Lower row of opponent cards (9- and 3-o'clock)
OPP_LOWER_Y = HAND_Y + 3 * Y_SPACING

# 9- and 10-o'clock opponent X-coord
OPP_9_10_X = MARGIN + int(CARD_WIDTH / 2)

# 12-o'clock opponent X-coord
OPP_12_X = int(SCREEN_WIDTH / 2 - OPPONENT_WIDTH / 2 + CARD_WIDTH / 2)

# 11-o'clock opponent X-coord
OPP_11_X = int((SCREEN_WIDTH - 2 * OPPONENT_WIDTH) / 3 + CARD_WIDTH / 2)

# 1-o'clock opponent X-coord
OPP_1_X = (OPP_11_X + int((SCREEN_WIDTH - 2 * OPPONENT_WIDTH) / 3)
           + OPPONENT_WIDTH)

# 2- and 3-o'clock opponent X-coord
OPP_2_3_X = SCREEN_WIDTH - MARGIN - OPPONENT_WIDTH + int(CARD_WIDTH / 2)

# opponent card coordinates
OPPONENT_9 = (OPP_9_10_X, OPP_LOWER_Y)
OPPONENT_10 = (OPP_9_10_X, OPP_UPPER_Y)
OPPONENT_11 = (OPP_11_X, OPP_UPPER_Y)
OPPONENT_12 = (OPP_12_X, OPP_UPPER_Y)
OPPONENT_1 = (OPP_1_X, OPP_UPPER_Y)
OPPONENT_2 = (OPP_2_3_X, OPP_UPPER_Y)
OPPONENT_3 = (OPP_2_3_X, OPP_LOWER_Y)

# list of opponent coordinates for each player count
OPPONENTS = [
    [OPPONENT_12],                                                  # 2
    [OPPONENT_11, OPPONENT_1],                                      # 3
    [OPPONENT_9, OPPONENT_12, OPPONENT_3],                          # 4
    [OPPONENT_9, OPPONENT_11, OPPONENT_1, OPPONENT_3],              # 5
    [OPPONENT_9, OPPONENT_10, OPPONENT_12, OPPONENT_2, OPPONENT_3]  # 6
]

# Position of instructional message
MESSAGE_X = TALON_X
MESSAGE_Y = OPP_LOWER_Y + CARD_HEIGHT / 2

MIN_DIST = 10  # minimum distance recognized as 'arrived at target'
BURN_DELAY = 0.05
DEAL_DELAY = 0.5
TAKE_DELAY = 0.05
KILL_DELAY = 0.05

FONT_NAME = "Union"
DEFAULT_FONT_SIZE = 14
TEXT_FONT_SIZE = 12
TEXT_VERTICAL_OFFSET = CARD_VERTICAL_OFFSET / 2

BURN_DELAY = 0.05
DEAL_DELAY = 0.5
TAKE_DELAY = 0.05
KILL_DELAY = 0.05
AI_DELAY = 0.5

# English messages
MESSAGES_EN = {
    'SHOW_STARTER': ["Show {card} to start the game!",
                     "{name}'", "'shows starter card",
                     "",
                     ""],
    'FINISHED_SWAPPING': ["",
                          "{name}",
                          "finished swapping cards",
                          "",
                          ""],
    'DOES_NOT_SHOW': ["Show {card} to start the game!",
                      "{name}",
                      "does not show starter card",
                      "",
                      ""],
    'IS_OUT': ["",
               "{name}",
               "is out!",
               "",
               ""],
    'MAY_SWAP': ["{name}",
                 "you may swap face up table cards",
                 "with hand cards now",
                 "click <DONE> button, when ready",
                 ""],
    'IS_SWAPPING': ["",
                    "{name}",
                    "is swapping cards",
                    "",
                    ""],
    'TURN_NAME': ["",
                  "Turn {turn} {pdir}: {name} {thinking}",
                  "{tips[0]}",
                  "{tips[1]}",
                  "{tips[2]}"],
    'IS_SHITHEAD': ["",
                    "{name}",
                    "is the SHITHEAD",
                    "",
                    ""],
    'SHOW_OR_SKIP': ["Show {card} to start the game!",
                     "",
                     "{name}",
                     "click on {card} to show it",
                     "or <DONE> to skip"],
    'IS_STARTER': ["",
                   "{name}",
                   "is the starting player!!!",
                   "",
                   ""],
    'GAME_ABORTED': ["",
                     "!!! TOO MANY TURNS USED !!!",
                     "GAME ABORTED AFTER {turn} TURNS",
                     "",
                     ""]
}

# English tool tips
TIPS_EN = {
    'REFILL':   'Refill your hand',
    'END':      'End your turn',
    'TAKE':     'Take the discard pile',
    'KILL':     'Kill the discard pile',
    'HAND':     'Play hand card',
    'FUP':      'Play face up table card',
    'GET':      'Take face up table card',
    'FDOWN':    'Play face down table card',
    '2':        '2: next player may play any card',
    '3':        '3: it is transparent',
    '4':        '',
    '5':        '',
    '6':        '',
    '7':        '7: next player must play \u22647, no 10',
    '8':        '8: skip next player(s)',
    '9':        '',
    '10':       '10: kills the discard pile',
    'J':        '',
    'Q':        'Q: same player plays another card (any)',
    'K':        'K: change direction',
    'A':        ''
}


# -----------------------------------------------------------------------------
class CardSprite(arcade.Sprite):
    '''
    Sprites representing the cards in a shithead game.
    '''
    def __init__(self, card, scale=1):
        '''
        Initialize a card sprite.

        The card parameter references the card as it is seen by the game
        engine.  Its rank and suit attributes specifies the image rendered to
        display this card face up, while the id attribute specifies the image
        rendered, when it is displayed face down.

        :param card:    card represented by this sprite.
        :type card:     Card
        :param scale:   scale factor for displaying this card.
        :type scale:    float
    '''

        self.card = card
        self.speed = 0      # speed of card when it is moved.
        # image to be used for this card sprite if it's face up.
        # each of the card images is identified by suit and rank
        self.image = (f":resources:images/cards/card{self.card.suit}"
                      f"{self.card.rank}.png")

        # call the super class (arcade.Sprite) initializer
        # cards are initially rendered face down
        super().__init__(FACE_DOWN_IMAGE[self.card.did % 2], scale,
                         hit_box_algorithm='None')

    def face_down(self):
        """
        Turn the card face down.

        Multiple card decks are identified by their id.
        Cards from a deck with even id have red backs and cards from decks with
        odd id have blue backs.
        """
        # load the face down image into the sprite
        self.texture = arcade.load_texture(FACE_DOWN_IMAGE[self.card.did % 2])
        # reset the face up flag
        self.card.is_face_up = False

    def face_up(self):
        """
        Turn the card face up.
        """
        # load the face up image into the sprite
        self.texture = arcade.load_texture(self.image)
        # set the face up flag
        self.card.is_face_up = True

    @property
    def is_face_down(self):
        """
        Check if card is face down.

        :return:    True => card is face down.
        :rtype:     bool
        """
        return not self.card.is_face_up


# -----------------------------------------------------------------------------
class Message:
    """
    Print up to 5 lines of text to the screen.

    The message window is in the middle of the game screen above the talon.
    """

    def __init__(self):
        """
        Defines a text window used for instructional messages.

        """
        self.coords = (MESSAGE_X, MESSAGE_Y)    # center/top of message window
        self.n_lines = 5                        # number of lines
        self.color = arcade.color.WHITE         # text color
        self.font_size = TEXT_FONT_SIZE         # text size
        self.line_spacing = CARD_HEIGHT / 5     # distance between lines
        self.lines = []                         # list of text lines
        for _ in range(self.n_lines):
            self.lines.append('')               # initialize with empty lines

    def set_line(self, line_nbr, text):
        """
        Set text in specified line.

        :param line_nbr:    line number (0..n_lines-1)
        :type line_nbr:     int
        :param text:        text set in specified line.
        :type text:         str
        """
        if line_nbr >= 0 and line_nbr < self.n_lines:
            self.lines[line_nbr] = text
        else:
            raise ValueError(f"Line number {line_nbr} is outside of the text"
                             " window!")

    def draw_text(self):
        """
        Draw text to the screen.
        """
        for i, line in enumerate(self.lines):
            arcade.draw_text(
                    line,                       # displayed text
                    self.coords[0],             # x-coordinate of line center
                    # calculate y-coordinate of line top from line number
                    self.coords[1] - i * self.line_spacing,
                    self.color,                 # text color
                    self.font_size,             # font size
                    anchor_x='center',          # x-ccord => center of line
                    anchor_y='top',             # y-coord => top of line
                    font_name = FONT_NAME       # used font -> check unicodes
            )


# -----------------------------------------------------------------------------
class Place:
    """
    Card mover target.

    Keeps a list of coordinates where cards are placed on the screen.
    For 'talon', 'discard', and 'removed' this list has only one entry (0).
    For the players we have 4 entries, where the coordinates for the table
    cards are at index 0-2 and the coordinates for the hand cards at index 3.
    We also create a list per coordinate, where cards currently placed at this
    coordinate are listed. This allows us to keep count of the number of cards
    currently at each positiion. In case of the human player (marked with the
    'human' flag), the list of cards at the index 3 (hand cards) is also used
    to spread out the cards.
    The name is added to allow us to label the opponents.
    """

    def __init__(self, name, coords, human=False):
        """
        Initializer.

        Create an empty card list per coordinate pair specified for this place,
        i.e. in case of a player we have 3 lists for the table cards and 1 for
        the hand cards.
        In case of the player places create a text object for his name and
        place it below the middle table cards.
        Create an empty rectangle with bright green borders to mark this player
        as next player and a filled bright green rectangle to mark this player
        as current player.

        :param name:    'talon', 'removed', 'discard', or player name.
        :type name:     str
        :param coords:  list of coordinates (x/y-tuples).
        :type coords:   list
        :param human:   marks place as human player => spread hand cards.
        :type human:    bool
        """
        self.name = name
        self.coords = coords
        self.human = human
        self.cards = []  # list of cardlists per coordinate
        for _ in range(len(coords)):
            self.cards.append([])   # add empty list per coordinate
        # if this is a player place, create a text object with his name
        # below the middle table card
        if len(coords) > 1:
            self.label = arcade.Text(
                name,
                coords[1][0],
                coords[1][1] - CARD_HEIGHT/2 - TEXT_VERTICAL_OFFSET,
                arcade.color.WHITE,
                DEFAULT_FONT_SIZE,
                anchor_x='center',
                anchor_y='top')
            # get width and height of text object
            w = self.label.content_width
            h = self.label.content_height
            # get position of text object
            x = self.label.x
            y = self.label.y
            # create an outline rectangle to mark this player as next player
            self.frame_next = arcade.create_rectangle_outline(
                x, y - h/2, w+6, h+4, arcade.color.BRIGHT_GREEN, 3, 0)
            # create a filled rectangle to mark this player as current player
            self.frame_current = arcade.create_rectangle_filled(
                x, y - h/2, w+6, h+4, arcade.color.BRIGHT_GREEN, 0)

    def print(self):
        """
        Print place information.
        """
        print(f'{self.name}:')
        for i, coord in enumerate(self.coords):
            x, y = coord
            print(f' ({x},{y}),', end=' ')
            print(' '.join([str(card) for card in self.cards[i]]))


# -----------------------------------------------------------------------------
class CardMover:
    """
    Moves cards in its list to a target position.

    The mover is setup with a list of possible target places (talon, discard,
    removed, players) with sub-targets (0..2 => table cards, 3 => hand cards)
    in case of the players. So instead of telling the mover to move a card to
    coords X/Y, we now just tell him to move the card to player: 'name'
    index: 2 (= last of the table cards).
    We don't need the source coords, since each of the card sprite knows where
    it is at any time.
    We call its update() method from Shithead.on_update(), i.e. about 60 times
    per second.
    Cards which have to be moved to a new target position, are added to a list
    together with the destination place (name, index), a delay time, and a flag
    which specifies, whether the card has to be placed face up or face down at
    the target location. Move list entries have the format:
        (card, name, idx, delay, face_up) with:
            - card      => card to be moved
            - name      => name of the target place
                           ('talon', 'removed', 'discard', or player name)
            - idx       => index of target place's card list (0..3)
            - delay     => delay [s] after which card starts moving
            - face_up   => place card face up at target if True.
    By setting the 'started flag' the 'time' attribute is reset to 0 and moving
    of the cards in the move_list starts.
    With the 'started' flag set, the 'time' attribute is incremented by the
    delta_time parameter in its update() method.
    In the update() method we check for each entry in the move_list, if it's
    time to start moving this card (delay <= time).
    If this is the case and the card is not moving yet, we set dx and and dy of
    the card, to move it in the direction of its target position.
    If the card is already moving we check its distand to the target position.
    If the the distance would grow again with the next update, we have reached
    the target position, i.e. the position of the card is set to the target
    coords and dx/dy are reset to 0. The card is flipped face up or down as
    requested and its entry is removed from the move list.
    As soon as the move list is empty the 'started' flag will be reset,
    i.e. the move job is complete.
    """

    def __init__(self, mat_list, sprite_list, card2sprite, card_speed=20):
        """
        Initializer.

        Creates attributes:
            - started       True => started moving cards in list.
            - time          Time passed since moving has started.
            - move_list     list of cards to be moved.
            - places        dictionary with possible targets.
            - hand          list of cards in hand of human player.

        :param mat_list:    sprite list used to draw fixed card mats.
        :type mat_list:     SpriteList.
        :param sprite_list: sprite list used to draw moving cards.
        :type sprite_list:  SpriteList.
        :param card2sprite: card-to-sprite map
        :type card2sprite:  dict
        :param card_speed:  card animation speed (10, 20, 30, 40, 50)
        :type card_speed:   int
        """
        # reference to sprite list for fixed card mat sprites
        self.mat_list = mat_list
        # reference to sprite list for moving card sprites
        self.sprite_list = sprite_list
        # dictionary to find the sprite belonging to a card
        self.card2sprite = card2sprite
        # set card animation speed
        self.card_speed = card_speed
        self.started = False    # True => increment time
        self.time = 0  # incrementing after mover has been started
        self.move_list = []  # list of cards to be moved
        # dictionary of possible targets (key = name of target)
        self.places = {}

    def add_place(self, name, coords, human=False):
        """
        Add a place to the card mover's list of places.

        :param name:    'talon', 'removed', 'discard', or player name.
        :type name:     str
        :param coords:  list of coordinates (x/y-tuples).
        :type coords:   list
        :param human:   marks place as human player => spread hand cards.
        :type human:    bool
        """
        # create this place and add it to the dictionary.
        self.places[name] = Place(name, coords, human)

    def setup_core_mats(self):
        """
        Creates mats for talon, discard pile and removed cards.

        Creates dark green sprites and positions them at the predefined
        locations.
        Creates the corresponding card mover places.
        Adds the created sprites to the mat sprite list.
        """
        # create mat where talon is placed on the screen
        mat = arcade.SpriteSolidColor(
            CARD_WIDTH, CARD_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        mat.position = (TALON_X, TALON_Y)
        # add it to the mover places
        self.add_place('talon', [(TALON_X, TALON_Y)])
        # add it to the mat sprite list
        self.mat_list.append(mat)

        # create mat where discard pile is placed on the screen
        mat = arcade.SpriteSolidColor(
            CARD_WIDTH, CARD_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        mat.position = (DISCARD_X, DISCARD_Y)
        # add it to the mover places
        self.add_place('discard', [(DISCARD_X, DISCARD_Y)])
        # add it to the mat sprite list
        self.mat_list.append(mat)

        # create mat where cards removed from the game are placed
        mat = arcade.SpriteSolidColor(
            CARD_WIDTH, CARD_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
        mat.position = (REMOVED_X, REMOVED_Y)
        # add it to the mover places
        self.add_place('removed', [(REMOVED_X, REMOVED_Y)])
        # add it to the mat sprite list
        self.mat_list.append(mat)

    def setup_ai_player_mats(self, name, left_xy):
        """
        Setup mats for 1 AI player.

        Creates 4 dark green sprites indicating where an opponent's cards are
        displayed (0..2 => table cards, 3 => hand cards).
        Creates the corresponding card mover place.
        Adds the created sprites to the mat sprite list.

        :param name:    name of opponent player.
        :type name:     str
        :param left_xy:  X/Y-coordinates of leftmost opponent mat.
        :type left_xy:   tuple
        """
        x, y = left_xy
        coords = []  # list of coordinates from left to right
        for i in range(4):
            coords.append((x + i * X_SPACING, y))
            mat = arcade.SpriteSolidColor(
                CARD_WIDTH, CARD_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
            mat.position = coords[i]
            # add sprite to the mat sprite list
            self.mat_list.append(mat)
        # add this opponent to the card mover places.
        self.add_place(name, coords)

    def setup_opponent_mats(self, players):
        '''
        Setup the opponent (AI) player mats.

        Specifies the coords of the leftmost mat for each of the opponents
        depending on the number of players.
        There are 2 rows of possible opponent places named after clock hours at
        the top of the screen:
            2 players:              12:00

            3 players:        11:00        1:00

            4 players:              12:00
                         9:00                     3:00

            5 players:        11:00        1:00
                         9:00                     3:00

            6 players:  10:00       12:00         2:00
                         9:00                     3:00

        Creates for each of these coords a set of dark green mats for the table
        (0..2) and hand cards (3) of the AI players and adds them to the mat
        sprite list and also to the list of mover target places.

        :param players:     list of players (human player at index 0)
        :type players:      list
        '''
        # get number of players
        n_players = len(players)

        # get list of opponent coordinates for this number of players
        opp_coords = OPPONENTS[n_players - 2]

        # create opponent mats
        for i in range(n_players-1):
            # setup the mat sprites and add them to the mat sprite list
            # create the target place and add it to the mover's place list
            self.setup_ai_player_mats(players[i+1].name, opp_coords[i])

    def setup_human_player_mats(self, name):
        """
        Setup the human player mats.

        The human player is always at the bottom of the screen with 3 table
        card mats in the center (below talon and discard pile) and space below
        them to spread out the hand cards.
        Creates dark green sprites indicating where the human player's table
        are displayed and adds them to the mat sprite list.
        Creates the corresponding card mover place and adds it to the mover's
        target list.

        :param name:    name of player.
        :type name:     str
        """
        hand_xy = (HAND_X, HAND_Y)  # X/Y-coords of central hand card.
        x, y = (TABLE_X, TABLE_Y)   # X/Y-coords of leftmost table card mat.

        # list of coordinats: hand + table from left to right
        coords = []
        for i in range(3):
            # create table card mats and assign them to coords[0]..coords[2]
            coords.append((x + i * X_SPACING, y))
            mat = arcade.SpriteSolidColor(
                CARD_WIDTH, CARD_HEIGHT, arcade.csscolor.DARK_OLIVE_GREEN)
            mat.position = coords[i]
            # add sprite to the mat sprite list
            self.mat_list.append(mat)
        # there's no mat for the hand cards (-> spread_out_hand()),
        # but the coords of the central hand card are in coords[3]
        coords.append(hand_xy)
        # add the human player to the card mover places ().
        self.add_place(name, coords, True)

    def add(self, card, name, idx, delay, face_up=False):
        """
        Add a card to the move list.

        Uses the name of the target and the index (always 0 for core places,
        0..2 for player table cards, and 3 for hand cards) into the coords list
        of this place, to add the actual target coordinates.
        Cards can only be added, if the move has not been already started.

        :param card:        card to be moved.
        :type CardSprite:   Card
        :param name:        name of target place.
        :type name:         str
        :param idx:         index into coords list of this place
        :type idx:          int
        :param delay:       delay [s] before this card starts moving.
        :type delay:        float
        :param face_up:     True => place card face up after reaching target.
        :type face_up:      bool
        """
        if self.started:
            raise ValueError("Can't add card to already started move!")
        else:
            target = self.places[name].coords[idx]
            self.move_list.append((card, name, idx, target, delay, face_up))

    def start(self):
        """
        Set 'started' flag to start moving cards.
        """
        if self.started:
            raise ValueError("Moving cards has already been started!")
        else:
            self.started = True

    def is_started(self):
        """
        Get 'started' flag.

        :return:    'started' flag.
        :rtype:     bool
        """
        return self.started

    def hide_hand_cards(self, name):
        """
        Turn all hand cards of specified player face down.

        This is used after the starting player auction to turn all shown AI
        player cards face down again.

        :param name:    name of player.
        :type name:     str
        """
        if name in self.places:
            for card in self.places[name].cards[3]:
                card.face_down()
        else:
            raise ValueError(f"Unknown player {name}!")

    def spread_out_hand(self, cards):
        """
        Add position data to cards in human player's hand.

        TODO remove 'cards' parameter, it's always the human player's hand.

        :param cards:   list of hand cards
        :type cards:    list of CardSprites
        """
        # no cards left in hand => do nothing
        if len(cards) == 0:
            return

        # create an empty Deck in order to use it's sort() method and add the
        # hand cards to it.
        hand = Deck(empty=True)
        for card_sprite in cards:
            # add Card objects referenced by card sprites to hand
            # => we can use the Deck class methods (sort, etc.)
            hand.add_card(card_sprite.card)

        # make sure the hand is sorted
        hand.sort()

        # get the number of different ranks in this hand
        # => number of columns necessary to display this cards
        cols = hand.get_nof_ranks()

        # calculate the width of the whole spread
        # as card widths + gap widths
        width = cols * X_SPACING - CARD_WIDTH * HORIZONTAL_MARGIN_PERCENT
        # calculate X-coord of leftmost column
        col_x = (HAND_X - width / 2) + (CARD_WIDTH / 2)
        rank = hand[0].rank
        offset = 0
        for card in hand:
            if card.rank != rank:
                # start of next column
                col_x += X_SPACING
                offset = 0
                rank = card.rank
            # find the sprite belonging to this card
            for card_sprite in cards:
                if card_sprite.card == card:
                    break
            else:
                raise ValueError("Card sprite doesn't exist!")
            card_sprite.position = (col_x, HAND_Y - offset)
            # pull it to the top of the sprite list
            self.sprite_list.remove(card_sprite)
            self.sprite_list.append(card_sprite)
            # fan out cards with same rank
            offset += CARD_VERTICAL_OFFSET

    def fan_out_discard(self):
        """
        Fan out the cards at the top of the discard pile.

        Players should be able to see how many cards of same rank are at the
        top of the discard pile and the rank of the 1st card following 1 or
        more '3's at the top.
        Get the number of visible cards at the top of the discard pile.
        Add position data to cards in discard pile in a way, that all cards up
        to the first visible card get the position of the discard pile, while
        the top cards are fanned out to the right.
        """
        # get the list of cards in the discard pile
        cards = self.places['discard'].cards[0]
        discard = Discard()
        for card_sprite in cards:
            # add Card objects referenced by card sprites to discard
            # => we can use the Discard class method get_ntop_visible()
            discard.add_card(card_sprite.card)
        # get the number of visible cards at the top of the discard pile.
        ntop = discard.get_ntop_visible()

        # fan cards so that ntop cards are visible
        for i, card in enumerate(cards):
            if i > len(cards) - ntop:
                # fanned out cards
                off = (i - len(cards) + ntop) * CARD_HORIZONTAL_OFFSET
            else:
                # cards up to the 1st visible card
                off = 0
            card.position = (DISCARD_X + off, DISCARD_Y)

    def find_source(self, card):
        """
        Find place where card starts from.

        We need the source place of this card in order to remove the card from
        the places card list => update its card count.

        :param card:    card for which we want to find its source place.
        :type card:     Card
        :return:        name of source, index of card list.
        :rtype:         tuple
        """
        for name, place in self.places.items():
            for idx, card_list in enumerate(place.cards):
                if card in card_list:
                    return (name, idx)
        # if we get here, something is wrong
        raise ValueError(f"Card mover couldn't find {str(card)}!")

    def get_delay(self):
        """
        Get delay of last move list entry.

        :return:        delay of last move list entry [s].
        :rtype:         float
        """
        return self.move_list[-1][4]

    def launch_card(self, card):
        """
        Start moving a card.

        Sets the card's speed and removes it from the source.

        :param card:    card which starts to move.
        :type card:     CardSprite.
        """
        # pull it to the top of the sprite list
        self.sprite_list.remove(card)
        self.sprite_list.append(card)
        # card starts moving => set speed > 0
        card.speed = self.card_speed
        # find where this card starts from
        name, src_idx = self.find_source(card)
        # and remove it from the source's card list
        self.places[name].cards[src_idx].remove(card)
        # if it was removed from the human player's hand,
        # we have to rearrange his hand cards
        if self.places[name].human and src_idx == 3:
            self.spread_out_hand(self.places[name].cards[src_idx])

    def move_card(self, card, target):
        """
        Move card towards its destination.

        Calculates the new position of the card if moving with the card speed
        towards the target coordinates. By comparing the distance between old
        card position and target to the distance between new position and
        target we can check if the card has arrived at the target. If the mew
        position is farther away, we are overshooting, i.e. the card has
        arrived at its destination and needs to stop at the target coordinates.

        :param card:    moving card.
        :type card:     CardSprite
        :param target:  target coordinates.
        :type target:   tuple
        """
        x_trg, y_trg = target   # target x/y
        x_src = card.center_x   # source x
        y_src = card.center_y   # source y
        # get angle target/card-center
        rad = arcade.get_angle_radians(x_trg, y_trg, x_src, y_src)
        # calculate change of card position
        delta_x = -card.speed * math.sin(rad)
        delta_y = -card.speed * math.cos(rad)

        # calculate distance to target from old position
        dist = arcade.get_distance(x_trg, y_trg, x_src, y_src)
        # calculate distance to target from new position
        dist_new = arcade.get_distance(
                x_trg, y_trg, x_src + delta_x, y_src + delta_y)
        if dist_new >= dist:
            # card would overshoot target => stop at target coordinates
            card.speed = 0
            card.center_x = x_trg
            card.center_y = y_trg
        else:
            # continue to move towards the target
            card.center_x += delta_x
            card.center_y += delta_y

    def update(self, delta_time):
        """
        Update cards in move list.

        Called about 60 times per second by the arcade window update function.
        Immediately returns if moving the cards in the move list has not been
        activated by setting the started flag.
        If the started flag was set, add the time expired since the last call
        to the time attribute.
        Loop through all entries in the move list and check for each card which
        is not already moving, if it is time to start moving.
        For moving cards (i.e. speed > 0) we check if they have reached their
        target position. If this is the case, we place the card face up or face
        down as specified at the target position and reset the speed to 0. We
        then remove the corresponding entry from the move list.
        Otherwise, we move the card towards its target.
        Finally, we check if the move list is empty and reset the 'started'
        flag and the 'time' attribute, if this is the case.

        :param delta_time:      time since method was called the last time.
        :type delta_time:       float
        :return:                True => moving cards ongoing, False => finished
        :rtype:                 bool
        """
        if not self.started:
            return False  # nothing to do

        # increment the time
        self.time += delta_time

        # check move list
        for move_list_idx, move in enumerate(self.move_list):
            # unpack details from move list entry
            card, name, trg_idx, target, delay, face_up = move
            # check if it's time for this card to start moving
            if card.speed == 0 and delay <= self.time:
                # card starts moving
                self.launch_card(card)

            # card is moving
            if card.speed > 0:
                self.move_card(card, target)
                if card.speed == 0:
                    # has stopped at target
                    if face_up:
                        card.face_up()
                    else:
                        card.face_down()
                    # add card to target's card list
                    self.places[name].cards[trg_idx].append(card)
                    if self.places[name].human and trg_idx == 3:
                        # card was moved to the human player's hand
                        # => re-arrange cards
                        card.face_up()
                        self.spread_out_hand(self.places[name].cards[trg_idx])
                    elif name == 'discard':
                        # fan out cards of same rank at the top
                        # of the discard pile
                        self.fan_out_discard()

                    # remove it from the move list
                    self.move_list.pop(move_list_idx)

        # check if all cards have reached their target
        if len(self.move_list) == 0:
            self.started = False
            self.time = 0
            return False    # finished moving cards
        else:
            return True     # not finished moving cards

    def draw_talon_count(self):
        '''
        Draw number of cards below talon.
        '''
        arcade.draw_text(
                str(len(self.places['talon'].cards[0])),
                TALON_X,
                TALON_Y - CARD_HEIGHT/2 - TEXT_VERTICAL_OFFSET,
                arcade.color.WHITE,
                DEFAULT_FONT_SIZE,
                anchor_x='center',
                anchor_y='top',
                font_name = FONT_NAME)

    def draw_discard_count(self):
        '''
        Draw number of cards below discard pile.
        '''
        # draw number of cards below discard pile
        arcade.draw_text(
                str(len(self.places['discard'].cards[0])),
                DISCARD_X,
                DISCARD_Y - CARD_HEIGHT/2 - TEXT_VERTICAL_OFFSET,
                arcade.color.WHITE,
                DEFAULT_FONT_SIZE,
                anchor_x='center',
                anchor_y='top',
                font_name = FONT_NAME)

    def draw_removed_count(self):
        '''
        Draw number of cards below removed cards.
        '''
        arcade.draw_text(
                str(len(self.places['removed'].cards[0])),
                REMOVED_X,
                REMOVED_Y - CARD_HEIGHT/2 - TEXT_VERTICAL_OFFSET,
                arcade.color.WHITE,
                DEFAULT_FONT_SIZE,
                anchor_x='center',
                anchor_y='top',
                font_name = FONT_NAME)

    def draw_opponent_count(self, players):
        '''
        Draw number of cards below opponents hand cards.

        :param players:     List of players.
        :type players:      list
        '''
        for player in players:
            if isinstance(player, HumanPlayer):
                continue    # skip number of hand cards for human player

            # draw number of cards below opponent hand cards
            arcade.draw_text(
                    str(len(self.places[player.name].cards[3])),
                    self.places[player.name].coords[3][0],
                    (self.places[player.name].coords[3][1]
                     - CARD_HEIGHT/2 - TEXT_VERTICAL_OFFSET),
                    arcade.color.WHITE,
                    DEFAULT_FONT_SIZE,
                    anchor_x='center',
                    anchor_y='top',
                    font_name = FONT_NAME)

    def draw_player_names(self, state):
        '''
        Draw names of players  below table cards.

        Draws names of players below table cards and also marks the current
        player with a full bright green rectangle and the next player with a
        outlined bright green rectangle.

        :param state:   current game state
        :type state:    State
        '''
        players = state.players     # list of players
        cur = state.player          # index of current player
        nxt = state.next_player     # index of next player
        for idx, player in enumerate(players):
            if idx == cur:
                # filled rectangle behind current player's name
                self.places[player.name].frame_current.draw()
            elif idx == nxt:
                # outlined rectangle around next player's name
                self.places[player.name].frame_next.draw()
            # draw the player name below the center table card
            self.places[player.name].label.draw()


# -----------------------------------------------------------------------------
class GameView(arcade.View):
    """ View where the actual game is played """

    def create_players(self):
        """
        Create players from players configuration (name, type).

        human players, are created to use the gui and to automatically end
        their turn if no other options are left (fast game option).
        AI players are create to use the provided lookup table for card
        swapping. Their type can directly be looked up in the player module
        (imported as plr) to get the class which has to be instantiated.
        !!! NOTE !!!
        'DeeperShit' is an improved version of 'DeepShit' using MTCS in the end
        game. Instead of adding it as new AI type, we replace 'DeepShit' with
        'DeeperShit', i.e. the user still selects 'DeepSheet' but an AI player
        using 'DeeperShit' is created.

        :return:                list of player objects for this game.
        :rtype:                 list
        """
        # load lookup table from file in package, we need it to create the AI
        # players.
        fup_table = FupTable()
        fup_table.load(FUP_TABLE_FILE, True)

        players = []
        for player in self.config['players']:
            name, ptype, _ = player
            # change 'DeepShit' to 'DeeperShit'
            if ptype == 'DeepShit':
                ptype = 'DeeperShit'

            if ptype == 'Human':
                # create a human player with specified name, who's using the
                # gui and automatically ends his turn if there's no other
                # option.
                players.append(plr.HumanPlayer(name, True, True))
            else:
                try:
                    # ptype specifies the AiPlayer sub-class in the player
                    # module.
                    ai_player_class = getattr(plr, ptype)
                except AttributeError:
                    # skip empty player slots (type = '---')
                    ai_player_class = None
                if ai_player_class:
                    # create this AI player with the specified name
                    # that uses the lookup table for card swapping.
                    players.append(ai_player_class(name, fup_table))
        return players

    def create_statistics(self):
        """
        Create statistics from players configuration (name, counters).

        :return:    statistics.
        :rtype:     Statistics
        """
        # create a Statistics object
        stats = Statistics()
        for player in self.config['players']:
            name, ptype, counters = player
            if ptype != '---':   # skip players which are not in the game
                stats.set_stats(name, counters)
        return stats

    def __init__(self, config):
        """
        Game Initializer.

        Opens a green window of predefined size.
        Sets the players list.
        Sets the message dictionary.
        Initializes all attributs, but the actual setup happens in the setup()
        method, which can also be called to start a new round of the game.

        :param config:  Game configuration.
        :type config:   dict

        """

        # Initialize the super class
        # and title.
        super().__init__()

        # store the config (used by ResultView to start next game)
        self.config = config

        # create the list of players from the players in the configuration.
        self.players = self.create_players()
        self.n_players = len(self.players)

        # extract the game statistics from the players in the configuration
        self.stats = self.create_statistics()

        # no need to click to continue the game
        self.fast_play = config['fast_play']

        # set the card animation speed from config
        self.card_speed = int(self.config['card_speed'])

        # initialize game state
        self.state = None

        # flag to mark dealing of cards.
        self.dealing = False

        # flag set to wait for the human player to click anywhere
        self.wait_for_human = False

        # name of this round's shithead
        self.shithead = None

        # 'aborted' flag set in case of an AI deadlock
        self.aborted = False

        # sprite list with all cards, no matter where they are
        self.card_list = None

        # mat list for talon, discard pile, removed cards, opponent cards,
        # and human player cards.
        self.mat_list = None

        # dictionary to map cards to card-sprites
        self.card2sprite = None

        # card mover moves card sprites from one place to another
        self.mover = None

        # 'DONE' button
        self.button = None
        self.button_text = None

        # Text window for instructional messages
        self.message = None

        # Wait timer to implement delays
        self.wait_time = 0

        # set message dictionary
        self.msg_dict = MESSAGES_EN

        # set tips dictionary
        self.tips_dict = TIPS_EN

        # counter for '...' animation
        self.thinking_cnt = 0

        # thinking animation
        self.thinking = ['   ', '.  ', '.. ', '...']

        # tool tips
        self.tips = ['', '', '']

        # set the background color to amazon green.
        arcade.set_background_color(arcade.color.AMAZON)

    def setup_end_turn_button(self):
        """
        Creates 'DONE' button sprite and text object.

        Creates a button sprite.
        Adds the created button sprite to the mat sprite list.
        Creates the 'DONE' text object.
        """
        self.button = arcade.Sprite(
            BUTTON_RELEASED, BUTTON_SCALE, hit_box_algorithm='None')
        self.button.position = (BUTTON_X, BUTTON_Y)
        self.mat_list.append(self.button)

        # create button text TODO context sensitive
        self.button_text = arcade.Text(
            'DONE',
            BUTTON_X,
            BUTTON_Y,
            arcade.color.WHITE,
            DEFAULT_FONT_SIZE,
            anchor_x='center',
            anchor_y='center')

    def draw_button_text(self):
        '''
        Draw 'DONE' button label.
        '''
        self.button_text.draw()

    def release_button(self):
        '''
        Load image of released button into sprite.
        '''
        self.button.texture = arcade.load_texture(BUTTON_RELEASED)

    def press_button(self):
        '''
        Load image of pressed button into sprite.
        '''
        self.button.texture = arcade.load_texture(BUTTON_PRESSED)

    def create_card_sprites(self):
        """
        Create card sprites.

        Creates for each card in the talon a sprite.
        Set position of all card sprites to talon's position.
        Adds all card sprites to the sprite list.
        Adds each sprite to the card2sprite lookup dictionary.
        """
        # for each card in talon create a sprite and add talon's coords to
        # this card sprites
        for card in self.state.talon:
            # create a sprite for this card
            sprite = CardSprite(card)
            # set the scale
            sprite.scale = CARD_SCALE
            # give each card sprite the talon position
            sprite.position = (TALON_X, TALON_Y)
            # and add it to the sprite list
            self.card_list.append(sprite)
            # and to the mover's talon list
            self.mover.places['talon'].cards[0].append(sprite)
            # and finally to the card-to-sprite map
            self.card2sprite[card] = sprite

    def create_single_card_sprite(self, card, name, index):
        """
        Create single card sprite and add it to place.

        Creates for specified card a sprite.
        Sets its position according to place coordinates at index.
        Adds sprite to place's card list at index.
        Adds card sprite to the sprite list.
        Adds sprite to the card2sprite lookup dictionary.

        :param card:    card for which the sprite is created.
        :type card:     Card
        :param name:    name of place where this sprite is created.
        :type name:     str
        :param index:   index of coords/card-list inside this place.
        :type index:    int
        """
        # create a sprite
        sprite = CardSprite(card)
        if card.is_face_up:
            sprite.face_up()
        # set the scale
        sprite.scale = CARD_SCALE
        # set position according to place at index
        sprite.position = self.mover.places[name].coords[index]
        # and add it to the sprite list
        self.card_list.append(sprite)
        # and to the place's card list
        self.mover.places[name].cards[index].append(sprite)
        # and finally to the card-to-sprite map
        self.card2sprite[card] = sprite
        # if card has been added to the humam's hand => spread out cards
        if self.mover.places[name].human and index == 3:
            self.mover.spread_out_hand(self.mover.places[name].cards[index])

    def move_burnt_cards(self):
        """
        Move the burnt cards from the talon to the removed cards pile.

        For some player counts a semi-random number of cards is removed from
        the game to avoid overlong games. For each removed card we program an
        animation sequence in the card mover, which lets us see how the top
        card of the talon is moved to the removed cards pile.
        """
        # loop through the cards in the burnt cards pile
        for i, card in enumerate(self.state.burnt):
            # get sprite belonging to this burnt card
            # note, that it still has the talon coords as position
            sprite = self.card2sprite[card]
            # program animation of moving top talon card to removed cards
            self.mover.add(sprite, 'removed', 0, i * BURN_DELAY, False)

    def move_dealt_cards(self):
        """
        Deals 9 cards to each of the players.

        Cards are dealt 1 after another from the top of the talon to the
        players.
            - 1 face down card to each player's 1st table mat.
            - 1 face down card to each player's 2nd table mat.
            - 1 face down card to each player's 3rd table mat.
            - 1 face up card to each player's 1st table mat.
            - 1 face up card to each player's 2nd table mat.
            - 1 face up card to each player's 3rd table mat.
            - 3x 1 face down card to each players hand mat.
              hand cards for the human player (always starting as players[0])
              are turned face up and spread out.
        For each of the cards we program an animation sequence in the card
        mover, showing how it is moved from the talon to the corresponding
        player's table or hand cards.
        !!!NOTE!!!
        This method must be called before the 'DEAL' play is applied, since it
        relies on finding the to be dealt cards on the talon.
        """
        players = self.state.players
        n_players = len(self.state.players)
        # the player following the dealer in clockwise direction
        # gets the first card.
        first = (self.state.dealer + 1) % n_players
        # get the delay of the last card mover entry
        if len(self.mover.move_list) > 0:
            # start dealing cards 1 s after last burnt card started moving
            off = self.mover.get_delay() + 1
        else:
            # no burnt cards => start dealing immediately
            off = 0
        # deal 9 cards from the talon to each player.
        for i in range(9 * n_players):
            # player following dealer in clockwise direction gets the 1st card
            player = players[(first + i) % n_players]
            # deal cards from the top of the talon
            # don't remove the cards from the talon, it will be done when the
            # 'DEAL' play is applied to the game state.
            card = self.state.talon[-(i+1)]
            sprite = self.card2sprite[card]
            if i < n_players * 3:
                # 3 face down table cards
                fup = False
                idx = int(i / n_players)
            elif i < n_players * 6:
                # 3 face up table cards
                fup = True
                idx = int(i / n_players) - 3
            else:
                # 3 face down hand cards
                fup = False
                idx = 3
            # program card mover to move this card from talon to player
            self.mover.add(sprite, player.name, idx, off + i * DEAL_DELAY, fup)

    def setup(self, shithead=None):
        """
        Game set up.

        Call this function to restart the game.
        Determines the number of players from the length of the player list.
        Creates a sprite list for all card sprites.
        Creates a sprite list for all mats, which are indicating places, where
        cards are played from/to (talon, discard pile, removed cards pile,
        player's table and hand cards).
        Creates a dictionary to lookup the sprite belonging to a card.
        Creates the card mover used to animate the moving of cards from one
        place to another.
        Setup the core mats for the talon, the discard pile, and the removed
        cards.
        Setup the mats for the table cards and the coordinates for the human
        player.
        Depending on the number of players, setup the mats for the opponent
        (AI) players.
        Setup the 'DONE' button.
        Setup the message window.
        Calculates the number of decks necessary for this number of players.
        Creates the initial game state:
            => copy of player list
            => determines the dealer
            => logging info
            => talon with specified number of decks
            => empty discard pile
            => empty burnt cards pile
            => empty removed cards pile
        Apply the 'SHUFFLE' play to the game state:
            => shuffled talon
        Create a card sprite for each card in the talon and add it to the
        sprite list and to the sprite lookup dictionary.
        Apply the 'BURN' play to the game state:
            => Depending on the number of players, some cards are removed from
               the talon and added to the the burnt cards pile.
        Program the card mover to show how these cards are moved (face down)
        from the talon to the removed cards pile.
        Program the card mover to show how 3 face down, 3 face up, and 3 hand
        cards are moved from the talon to each player.
        Apply the 'DEAL' play to the game state:
            => cards are dealt from talon to players in the game state.
        Start the card mover
            => show animation of burnt cards removal and dealing.

        :param shithead:  name of last rounds shithead, None => first round.
        :type shithead:   str
        """
        players = self.players

        # get number of players
        self.n_players = len(players)

        # create the sprite lists
        self.card_list = arcade.SpriteList()
        self.mat_list = arcade.SpriteList()

        # create the card-to-sprite map
        self.card2sprite = {}

        # create the card mover
        self.mover = CardMover(self.mat_list, self.card_list, self.card2sprite,
                               self.card_speed)

        # create mats for talon, discard pile, and removed cards
        self.mover.setup_core_mats()

        # create human player mats
        self.mover.setup_human_player_mats(players[0].name)

        # create opponent player mats
        self.mover.setup_opponent_mats(players)

        # create 'DONE' button
        self.setup_end_turn_button()

        # setup the message window
        self.message = Message()

        # find index of previous shithead in players list => dealer
        if shithead is not None:
            for idx, player in enumerate(self.players):
                if player.name == shithead:
                    dealer = idx
                    break
            else:
                raise ValueError(
                    f"Shithead {shithead} not found in list of players!")
        else:
            # very first round => select dealer randomly
            dealer = -1
        self.shithead = None    # shithead of this round not found yet
        self.aborted = False    # reset 'aborted' flag

        # calculate the number of necessary card decks
        n_decks = Game.calc_nof_decks(self.n_players)

        # create the logging info from the configuration
        log_level = self.config['log_level']
        log_to_file, log_debug, log_file = self.config['log_file']
        log_info = (log_level, log_to_file, log_debug, log_file)

        # if log-to-file has been selected, open the specified file for writing
        #  (=> reset file) and close it again.
        if log_info[1]:
            with open(log_info[3], 'w', encoding='utf-8') as log_file:
                log_file.write('--- Sh*thead Log-File ---\n')

        # create the initial game state with the original list of players,
        # the specified dealer (-1 => random, or shithead of previous round),
        # and the number of decks necessary for this number of players.
        self.state = State(players, dealer, n_decks, log_info)

        # shuffle the talon
        self.state = Game.next_state(
            self.state, Play('SHUFFLE'), None, self.stats)
        self.state.print()

        # create a card sprite for each card in the talon
        self.create_card_sprites()

        # remove some talon cards to match the player count
        self.state = Game.next_state(
            self.state, Play('BURN'), None, self.stats)
        self.state.print()
        # and program the card mover to show how these cards are moved to the
        # removed cards pile
        self.move_burnt_cards()

        # program the card mover to show how cards are moved from the talon to
        # the players.
        # Note, we do this before applying the 'DEAL' play, since it is easier
        # to get the moved cards from the talon.
        self.move_dealt_cards()

        # deal 3 face down, 3 face up, and 3 hand cards to each player
        self.state = Game.next_state(
            self.state, Play('DEAL'), None, self.stats)
        self.state.print()

        # start the card mover => animation of burning cards and dealing cards.
        self.mover.start()

        # set 'dealing' flag => no player actions till dealing is done
        self.dealing = True

    def setup_from_state(self, state_info):
        """
        Game set up from intermediate state.

        Function called to setup a game state logged with log-level 'Debugging'
        (=> JSON string).
        The GameView still has to be initialized with a configuration first.

        Call this function to restart the game.
        Determines the number of players from the length of the player list.
        Creates a sprite list for all card sprites.
        Creates a sprite list for all mats, which are indicating places, where
        cards are played from/to (talon, discard pile, removed cards pile,
        player's table and hand cards).
        Creates a dictionary to lookup the sprite belonging to a card.
        Creates the card mover used to animate the moving of cards from one
        place to another.
        Setup the core mats for the talon, the discard pile, and the removed
        cards.
        Setup the mats for the table cards and the coordinates for the human
        player.
        Depending on the number of players, setup the mats for the opponent
        (AI) players.
        Setup the 'DONE' button.
        Setup the message window.
        Creates the initial game state:
            => copy of player list
            => dealer from loaded state info
            => logging info reconstructed from loaded state info.
            => number of decks from loaded state info
            => talon with specified number of decks)
            => empty discard pile
            => empty burnt cards pile
            => empty removed cards pile
        From the loaded state info recreate:
            - the cards/sprites representing burnt cards.
            - the cards/sprites representing removed cards.
            - the cards/sprites representing talon cards.
            - the cards/sprites representing discarded cards.
            - the cards/sprites representing hand/table cards of each player.
        Recreate all other game state attributes (current player,
        direction, ...) from the loaded state info.

        :param state_info:  state information loaded from JSON file.
        :type state_info:   dict
        """
        players = self.players

        # get number of players
        self.n_players = len(players)

        # create the sprite lists
        self.card_list = arcade.SpriteList()
        self.mat_list = arcade.SpriteList()

        # create the card-to-sprite map
        self.card2sprite = {}

        # create the card mover
        self.mover = CardMover(self.mat_list, self.card_list, self.card2sprite,
                               self.card_speed)

        # create mats for talon, discard pile, and removed cards
        self.mover.setup_core_mats()

        # create human player mats
        self.mover.setup_human_player_mats(players[0].name)

        # create opponent player mats
        self.mover.setup_opponent_mats(players)

        # create 'DONE' button
        self.setup_end_turn_button()

        # setup the message window
        self.message = Message()

        # get index of the dealer from state info
        dealer = state_info['dealer']

        self.shithead = None    # shithead of this round not found yet
        self.aborted = False    # reset 'aborted' flag

        # get the number of necessary card decks from state info
        n_decks = state_info['n_decks']

        # create the logging info from the state info
        # => we can change it by editing the JSON string
        log_info = state_info['log_info']

        # create the initial game state with the original list of players,
        # the specified dealer (-1 => random, or shithead of previous round),
        # and the number of decks necessary for this number of players.
        self.state = State(players, dealer, n_decks, log_info)

        # load the burnt cards pile with burnt cards in state_info
        self.state.burnt.load_from_state(state_info['burnt'])
        self.state.n_burnt = state_info['n_burnt']
        # create a sprite for each burnt card
        for card in self.state.burnt:
            # create a sprite for this card
            # and give it the position of the removed cards pile
            # add the sprite to the sprite list
            # and to the removed cards pile list
            self.create_single_card_sprite(card, 'removed', 0)

        # load the removed cards pile with killed cards in state_info
        self.state.killed.load_from_state(state_info['killed'])
        # create a sprite for each killed card
        for card in self.state.killed:
            # add these sprites to the removed cards pile and the sprites list
            self.create_single_card_sprite(card, 'removed', 0)

        # load the talon with talon cards in state_info
        self.state.talon.load_from_state(state_info['talon'])
        # create a sprite for each talon card
        for card in self.state.talon:
            # add these sprites to the talon and the sprites list
            self.create_single_card_sprite(card, 'talon', 0)

        # load the discard pile with cards specified in state_info
        self.state.discard.load_from_state(state_info['discard'])
        for card in self.state.discard:
            # add these sprites to the discard pile and the sprites list
            self.create_single_card_sprite(card, 'discard', 0)

        # load player states
        # TODO if some players are already out this will result in an index out
        #      of range error
        for i, player in enumerate(self.state.players):
            player.load_from_state(state_info['players'][i])
            # create a sprite for each face down table card
            for j, card in enumerate(player.face_down):
                self.create_single_card_sprite(card, player.name, j)
            # create a sprite for each face up table card
            for j, card in enumerate(player.face_up):
                self.create_single_card_sprite(card, player.name, j)
            # create a sprite for each hand card
            for j, card in enumerate(player.hand):
                self.create_single_card_sprite(card, player.name, 3)

        # load remaining game state attributes
        self.state.turn_count = state_info['turn_count']
        self.state.player = state_info['player']
        self.state.direction = state_info['direction']
        self.state.next_direction = state_info['next_direction']
        self.state.next_player = state_info['next_player']
        self.state.n_played = state_info['n_played']
        self.state.eights = state_info['eights']
        self.state.kings = state_info['kings']
        self.state.game_phase = state_info['game_phase']
        self.state.starting_card = state_info['starting_card']
        self.state.auction_members = state_info['auction_members']
        self.state.shown_starting_card = state_info['shown_starting_card']
        self.state.result = state_info['result']
        # reset 'dealing' flag
        self.state.dealing = False

    def mark_talon(self):
        '''
        Draw bright green frame around talon.

        This is used to highlight the 'REfILL' play.
        '''
        arcade.draw_rectangle_outline(
                TALON_X, TALON_Y,               # position
                CARD_WIDTH+4, CARD_HEIGHT+4,    # size
                arcade.color.BRIGHT_GREEN,      # color
                3,                              # border width
                0)                              # tilt angle

    def mark_discard(self, discard):
        '''
        Draw bright green frame around discard pile.

        This is used to highlight the 'TAKE' and 'KILL' plays.

        :param discard:  discard pile
        :type discard:   Discard
        '''
        # get number of cards with same rank at top of discard pile
        ntop = discard.get_ntop()
        if discard.get_top_rank() == '3' and len(discard) > ntop:
            # if top card is '3' but there are other cards below the 3s.
            ntop += 1   # there's one more visible card at the top
        # highlight all visible cards at the top of the discard pile
        fan_width = CARD_WIDTH + (ntop - 1) * CARD_HORIZONTAL_OFFSET
        # calculate X-coordinate of rectangle center
        fan_x = DISCARD_X + (fan_width - CARD_WIDTH) / 2
        # highlight the discard pile
        arcade.draw_rectangle_outline(
                fan_x, DISCARD_Y,               # position
                fan_width+4, CARD_HEIGHT+4,     # size
                arcade.color.BRIGHT_GREEN,      # color
                3,                              # border width
                0)                              # tilt angle

    def mark_hand_cards(self, player, index, rank=True):
        '''
        Draw bright green frame around playable hand cards.

        This is used to highlight the 'HAND', 'PUT', and 'SHOW' plays.
        In case of 'HAND' and 'PUT', we can highlight all cards of same rank,
        while for 'SHOW' only the specified card is highlighted.

        :param player:  human player
        :type player:   Player
        :param index:   index of card in player hand.
        :type index:    int
        :param rank:    True => highlight all cards of this rank.
        :type rank:     bool
        '''
        # find card in player's hand
        card = player.hand[index]
        # find CardSprite belonging to this card
        sprite = self.card2sprite[card]
        # get number of cards with same rank as specified card in player's hand
        nof_cards = player.hand.get_nof_cards(card.rank)
        if rank:
            # calculate height of card column for this rank
            col_height = CARD_HEIGHT + (nof_cards - 1) * CARD_VERTICAL_OFFSET
            # calculate Y-coordinate of rectangle center
            col_y = HAND_Y - (col_height - CARD_HEIGHT) / 2
            # highlight the column of hand cards with this rank
            arcade.draw_rectangle_outline(
                    sprite.center_x, col_y,         # position
                    CARD_WIDTH+4, col_height+4,     # size
                    arcade.color.BRIGHT_GREEN,      # color
                    3,                              # border width
                    0)                              # tilt angle
        else:
            # highlight the specified hand card
            arcade.draw_rectangle_outline(
                    sprite.center_x, sprite.center_y,         # position
                    CARD_WIDTH+4, CARD_HEIGHT+4,    # size
                    arcade.color.BRIGHT_GREEN,      # color
                    3,                              # border width
                    0)                              # tilt angle

    def mark_fup_card(self, player, index):
        '''
        Draw bright green frame around a playable face up table card.

        This is used to highlight the 'FUP' and 'GET' plays.

        :param player:   human player
        :type player:    Player
        :param index:    index of card in player hand.
        :type index:     int
        '''
        # find card in player's face up table cards
        card = player.face_up[index]
        # find CardSprite belonging to this card
        sprite = self.card2sprite[card]
        # highlight this face up table card
        arcade.draw_rectangle_outline(
                sprite.center_x, sprite.center_y,   # position
                CARD_WIDTH+4, CARD_HEIGHT+4,        # size
                arcade.color.BRIGHT_GREEN,          # color
                3,                                  # border width
                0)                                  # tilt angle

    def mark_fdown_card(self, player, index):
        '''
        Draw bright green frame around face down table card.

        This is used to highlight the 'FDOWN' plays.

        :param player:   human player
        :type player:    Player
        :param index:    index of card in player hand.
        :type index:     int
        '''
        # find card in player's face up table cards
        card = player.face_down[index]
        # find CardSprite belonging to this card
        sprite = self.card2sprite[card]
        # highlight this face down table card
        arcade.draw_rectangle_outline(
                sprite.center_x, sprite.center_y,   # position
                CARD_WIDTH+4, CARD_HEIGHT+4,        # size
                arcade.color.BRIGHT_GREEN,          # color
                3,                                  # border width
                0)                                  # tilt angle

    def mark_end_turn(self):
        '''
        Draw bright green frame around 'DONE' button.

        This is used to highlight the 'END' play.
        '''
        arcade.draw_rectangle_outline(
                BUTTON_X, BUTTON_Y,                         # position
                self.button.width+4, self.button.height+4,  # size
                arcade.color.BRIGHT_GREEN,                  # color
                3,                                          # border width
                0)                                          # tilt angle

    def mark_human_legal_plays(self, state, dealing):
        '''
        Mark human players legal plays with bright green frames.

        :param state:   current game state
        :type state:    State
        :param dealing: True => card mover is dealing cards.
        :type dealing:  bool
        '''
        player = state.players[state.player]    # current player

        if (isinstance(player, AiPlayer) or dealing):
            return  # not human player or dealing cards

        # get legal plays for current player
        plays = state.get_legal_plays()
        for play in plays:
            if play.action == 'REFILL':
                self.mark_talon()
            elif play.action == 'END':
                self.mark_end_turn()
            elif play.action == 'HAND' or play.action == 'PUT':
                self.mark_hand_cards(player, play.index)
            elif play.action == 'TAKE' or play.action == 'KILL':
                self.mark_discard(state.discard)
            elif play.action == 'FUP' or play.action == 'GET':
                self.mark_fup_card(player, play.index)
            elif play.action == 'FDOWN':
                self.mark_fdown_card(player, play.index)
            elif play.action == 'SHOW':
                self.mark_hand_cards(player, play.index, False)
        return

    def on_draw(self):
        """
        Render the screen callback function.

        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        # clear the screen
        self.clear()

        # draw mats
        self.mat_list.draw()

        # draw 'DONE' text on button
        self.draw_button_text()

        # draw number of cards below talon
        self.mover.draw_talon_count()

        # draw number of cards below discard pile
        self.mover.draw_discard_count()

        # draw number of cards below removed cards
        self.mover.draw_removed_count()

        # draw number of cards below opponent hand cards
        self.mover.draw_opponent_count(self.state.players)

        # draw player names (with current/next indication)
        self.mover.draw_player_names(self.state)

        # mark human player's legal plays with bright green frames
        # after card moving has finished and as long as Shithead wasn't found.
        if (not self.mover.is_started() and len(self.state.players) > 1):
            self.mark_human_legal_plays(self.state, self.dealing)

        # draw message in instruction window
        self.message.draw_text()

        # draw the cards (last, so they are above all other elements)
        self.card_list.draw()

    def get_discard_play(self):
        """
        Get play corresponding to click on discard pile.

        If there are 4 or more cards of same rank at the top of the discard
        pile, clicking on the discard pile kills it (=> 'KILL').
        Otherwise, it means that the human player wants to take the discard
        pile on hand (=> 'TAKE').
        """
        if self.state.discard.get_ntop() >= 4:
            # discard pile can be killed
            return Play('KILL')
        else:
            # take the discard pile on hand
            return Play('TAKE')

    def get_hand_play(self, human, card):
        """
        Get play corresponding to click on human player's hand cards.

        During the SWAPPING_CARDS phase the clicked on card is put down as
        face up table card (=> 'PUT').
        During the FIND_STARTER phase the clicked on card is shown to become
        starting player (=> 'SHOW').
        During the PLAY_GAME phase the clicked on card is played on the discard
        pile (=> 'HAND').

        :param human:   human player.
        :type human:    Player
        :param card:    card referenced by the clicked on card sprite.
        :type card:     Card
        """
        # get the index of this card in the human's hand
        idx = human.hand.index(card)
        if self.state.game_phase == SWAPPING_CARDS:
            # put card from hand to face up table cards.
            return Play('PUT', idx)
        elif self.state.game_phase == FIND_STARTER:
            # show hand card in starter auction
            return Play('SHOW', idx)
        else:
            # play card from hand to discard pile
            return Play('HAND', idx)

    def get_face_up_play(self, human, card):
        """
        Get play corresponding to click on human player's face up table cards.

        During the SWAPPING_CARDS phase the clicked on card is taken on hand
        (=> 'GET').
        During the PLAY_GAME phase the clicked on card is either played on the
        discard pile (=> 'FUP'), if the player has no hand cards left, or taken
        on hand (=> 'GET') after taking the discard pile while playing from
        face up table cards.

        :param human:   human player.
        :type human:    Player
        :param card:    card referenced by the clicked on card sprite.
        :type card:     Card
        """
        # get the index of this card in the human's hand
        idx = human.face_up.index(card)
        if self.state.game_phase == SWAPPING_CARDS:
            # get card from face up table cards to hand
            return Play('GET', idx)
        elif len(human.hand) == 0:
            # play face up table card to discard pile
            return Play('FUP', idx)
        else:
            # pick face up table card after 'TAKE',
            # playing from face up table cards.
            return Play('GET', idx)

    def get_human_play(self, card_sprite):
        """
        Get play corresponding to a mouse click on a card.

        After the human player has clicked on a card, we check if this can be
        translated to a game play, depending on the card and the current game
        phase.
        Note, that the corresponding play will only be applied if it's also in
        the list of legal plays for the current game state.

        :param card_sprite:     top card the human player has clicked on.
        :type card:             CardSprite
        :return:                the corresponding play or None.
        :rtype:                 Play
        """
        # As long as he's in the game the human player is at index 0
        human = self.state.players[0]
        if not isinstance(human, plr.HumanPlayer):
            return None  # human player is no longer in the game => no play

        # get the card represented by this sprite
        card = card_sprite.card

        # check if click was on card at the top of the talon
        if self.state.talon and card == self.state.talon[-1]:
            return Play('REFILL')

        # check if it is at the top of the discard pile
        # since some of the cards at the top may be fanned out,
        # we have to check if the clicked card is in the discard pile.
        if self.state.discard and card in self.state.discard:
            return self.get_discard_play()

        # check if it is a hand card of the human player
        elif card in human.hand:
            return self.get_hand_play(human, card)

        # check if it is a face up table card of the human player
        elif card in human.face_up:
            return self.get_face_up_play(human, card)

        # check if it is a face down table card of the human player
        elif card in human.face_down:
            idx = human.face_down.index(card)
            return Play('FDOWN', idx)

        else:
            # must be opponent card or removed card => don't return a play.
            return None

    def set_message(self, message, turn=0, name='', thinking='', card='',
                    pdir='', tips=None):

        """
        Create multi-line message from message dictionary.

        Gets specified message from message dictionary.
        Evals each line to add variable elements like turn number, player name,
        or starting card and sets them in the message object.

        :param message:     name of message => key for message dictionary.
        :type message:      str
        :param turn:        turn number.
        :type turn:         int
        :param name:        player name.
        :type name:         str
        :param thinking:    '', '.', '..', or '...'
        :type thinking:     str
        :param card:        starting card.
        :type card:         Card
        :param pdir:        play direction symbol '\u21bb' => clockwise
                            or '\u21ba' => counterclockwise.
        :type pdir:         str
        :param tips:        tips to card under mouse (hover)
        :type tips:         list
        """
        for i, line in enumerate(self.msg_dict[message]):
            line = line.replace('{turn}', str(turn))
            line = line.replace('{name}', name)
            line = line.replace('{thinking}', thinking)
            line = line.replace('{card}', str(card))
            line = line.replace('{pdir}', pdir)
            if tips is not None:
                line = line.replace('{tips[0]}', tips[0])
                line = line.replace('{tips[1]}', tips[1])
                line = line.replace('{tips[2]}', tips[2])
            self.message.set_line(i, line)

    def get_play_delay(self, player):
        """
        Return play delay for human or AI players.

        In case of AI players we want a little bit of delay, so that the human
        player can better follow the action.

        :param player:  current player.
        :type player:   Player
        :return:        play delay [s]
        :rtype:         float
        """
        # is it the human player
        if isinstance(player, plr.HumanPlayer):
            # human player => move card immediately
            return 0
        else:
            # AI player => wait some time bevore moving cards
            return AI_DELAY

    def show_get_play(self, player, index):
        """
        Programs the card mover to move card to player's hand.

        Move card at index from table to hand during card swapping,
        or take one (or more of same rank) face up table cards on hand after
        taking the discard pile while playing from face up table cards.

        :param player:  current player.
        :type player:   Player
        :param index:   index of card in player's face up table cards.
        :type index:    int
        """
        # get the card at index in player's face up table cards
        card = player.face_up[index]
        # get sprite belonging to this card
        sprite = self.card2sprite[card]
        # get delay for human or AI
        delay = self.get_play_delay(player)
        # program card mover to move this card to the player's hand
        self.mover.add(sprite, player.name, 3, delay, False)

    def show_put_play(self, player, index):
        """
        Programs the card mover to move card to face up table cards.

        Put a card from player's hand to the face up table cards during card
        swapping.
        We have to find a mat for table cards with only a face down card on it.

        :param player:  current player.
        :type player:   Player
        :param index:   index of card in player's hand cards.
        :type index:    int
        """
        # get card at index in player's hand
        card = player.hand[index]
        # get the sprite belonging to this card
        sprite = self.card2sprite[card]
        # find the 1st table mat with only a face down card on it
        for idx in range(3):
            if len(self.mover.places[player.name].cards[idx]) == 1:
                break   # found a mat without face up table card
        else:
            # didn't find a mat without face up table card => something's wrong
            raise ValueError("Face up table cards already complete!")
        # get delay for human or AI
        delay = self.get_play_delay(player)
        # add card to mover list with found table slot as target
        self.mover.add(sprite, player.name, idx, delay, True)

    def show_show_play(self, player, index):
        """
        Shows a hand card face up during starting player auction.

        :param player:  current player.
        :type player:   Player
        :param index:   index of card in player's hand cards.
        :type index:    int
        """
        # get card at index in player's hand
        card = player.hand[index]
        # get the sprite belonging to this card
        sprite = self.card2sprite[card]
        # switch the card sprite face up
        sprite.face_up()
        # pull it to the top of the sprite list
        self.pull_to_top(sprite)
        # print instructions
        self.set_message('SHOW_STARTER', 0, player.name, '', card)
        if isinstance(player, plr.AiPlayer):    # AI player
            self.wait_time = 1
            if self.fast_play:
                # fast play => no need to click to continue
                self.wait_for_human = False
            else:
                # => wait for the human player to click anywhere
                self.wait_for_human = True

    def show_hand_play(self, player, index):
        """
        Programs the card mover to move a hand card to the discard pile.

        :param player:  current player.
        :type player:   Player
        :param index:   index of card in player's hand cards.
        :type index:    int
        """
        # get card at index in player's hand
        card = player.hand[index]
        # get the sprite belonging to this card
        sprite = self.card2sprite[card]
        # get delay for human or AI
        delay = self.get_play_delay(player)
        # add card to mover list with discard pile as target
        self.mover.add(sprite, 'discard', 0, delay, True)

    def show_refill_play(self, player):
        """
        Programs card mover to move the top talon cards to the player's hand.

        Move cards from the top of the talon to the players hand until either
        the hand has been refilled to 3 cards or the talon is empty.

        :param player:  current player.
        :type player:   Player
        """
        n_refilled = 3 - len(player.hand)
        if n_refilled > len(self.state.talon):
            # not enough cards in talon to refill to 3
            n_refilled = len(self.state.talon)
        # get delay for human or AI
        delay = self.get_play_delay(player)
        # get the list of talon card sprites
        cards = self.mover.places['talon'].cards[0]
        for i, sprite in enumerate(cards[::-1]):
            if i < n_refilled:
                # add talon cards sprites in reversed order to mover list
                # with player's hand as target
                self.mover.add(
                    sprite, player.name, 3, 2 * delay + i * TAKE_DELAY, False)

    def show_take_play(self, player):
        """
        Programs the card mover to move all discard pile cards to the player's
        hand.

        :param player:  current player.
        :type player:   Player
        """
        # get a list of all card sprites in the discard pile
        cards = self.mover.places['discard'].cards[0]
        # get delay for human or AI
        delay = self.get_play_delay(player)
        for i, sprite in enumerate(cards[::-1]):
            # add discard pile cards sprites in reversed order to mover list
            # with player's hand as target
            self.mover.add(
                sprite, player.name, 3, 2 * delay + i * TAKE_DELAY, False)

    def show_kill_play(self, player):
        """
        Programs the card mover to move all discard pile cards to the removed
        cards pile.

        :param player:  current player.
        :type player:   Player
        """
        # get a list of all card sprites in the discard pile
        cards = self.mover.places['discard'].cards[0]
        # get delay for human or AI
        delay = self.get_play_delay(player)
        for i, sprite in enumerate(cards[::-1]):
            # add discard pile cards in reversed order to mover list
            # with removed cards pile as target
            self.mover.add(
                sprite, 'removed', 0, 2 * delay + i * KILL_DELAY, False)

    def show_fup_play(self, player, index):
        """
        Programs card mover to move a face up table card to the discard pile.

        :param player:  current player.
        :type player:   Player
        :param index:   index of card in player's hand cards.
        :type index:    int
        """
        # get card at index in player's face up table cards
        card = player.face_up[index]
        # get the card sprite belonging to this card
        sprite = self.card2sprite[card]
        # get delay for human or AI
        delay = self.get_play_delay(player)
        # add card to mover list with discard pile as target
        self.mover.add(sprite, 'discard', 0, delay, True)

    def show_fdown_play(self, player, index):
        """
        Programs the card mover to move a face down table card to the discard
        pile.

        :param player:  current player.
        :type player:   Player
        :param index:   index of card in player's hand cards.
        :type index:    int
        """
        # get face down table card at index
        card = player.face_down[index]
        # get the card sprite belonging to this card
        sprite = self.card2sprite[card]
        # get delay for human or AI
        delay = self.get_play_delay(player)
        # add card to mover list with discard pile as target
        self.mover.add(sprite, 'discard', 0, delay, True)

    def show_end_play(self, player):
        """
        Print messages after player has ended his turn.

        :param player:  current player.
        :type player:   Player
        """
        # get the game phase
        phase = self.state.game_phase

        if phase == SWAPPING_CARDS:
            # player has finished swapping cards.
            # don't stop, just wait 1s
            self.set_message('FINISHED_SWAPPING', 0, player.name)
            self.wait_time = 1

        elif phase == FIND_STARTER:
            # player didn't show starting card
            suit = STARTING_SUITS[self.state.starting_card % 4]
            rank = STARTING_RANKS[self.state.starting_card // 4]
            card = Card(0, suit, rank)
            # don't stop if player couldn't show starter card, just wait 1s
            self.set_message('DOES_NOT_SHOW', 0, player.name, '', card)
            self.wait_time = 1

        else:
            # player has ended his turn during normal game play
            if isinstance(player, plr.AiPlayer):
                # end of AI turn during normal turns
                if self.fast_play:
                    # fast play => no need to click to continue
                    self.wait_for_human = False
                else:
                    # => wait for the human player to click anywhere
                    self.wait_for_human = True

    def show_play(self, play):
        """
        Programs the card mover to move cards according to this play.

        :param play:    a legal play of the current player.
        :type play:     Play
        """
        # get current player
        player = self.state.players[self.state.player]
        # get executed action and index of card (or -1) from this play.
        action = play.action
        index = play.index

        # handle the selected play
        if action == 'GET':
            self.show_get_play(player, index)

        elif action == 'PUT':
            # card swapping: move card from hand to table
            self.show_put_play(player, index)

        elif action == 'SHOW':
            # start player auction: show card in hand face up
            self.show_show_play(player, index)

        elif action == 'HAND':
            # play card from hand: move card at index from hand to discard pile
            self.show_hand_play(player, index)

        elif action == 'REFILL':
            # refill hand: move top card from talon to hand
            self.show_refill_play(player)

        elif action == 'TAKE':
            # take discard pile: move cards from discard pile to player's hand
            self.show_take_play(player)

        elif action == 'KILL':
            # kill the discard pile: move cards from discard pile to removed
            # cards
            self.show_kill_play(player)

        elif action == 'FUP':
            # play face up table card: move card at index from face up table
            # cards to discard pile
            self.show_fup_play(player, index)

        elif action == 'FDOWN':
            # play face down table card: move card at index from face down
            # table cards to discard pile
            self.show_fdown_play(player, index)

        elif action == 'END':
            # do nothing, game continues with next player
            self.show_end_play(player)

        elif action == 'OUT':
            # player is out => print message
            self.set_message('IS_OUT', 0, player.name)

        elif action == 'ABORT':
            # Too many turns (AI deadlock) => abort game.
            # nothing to show.
            pass

        else:
            raise ValueError(f"Unexpected action: {action}")

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Mouse button pressed event callback function.

        This function is called when the mouse button was pressed.
        If the human player (always at index 0 of the players list) is the
        current player, we check if the mouse is on one of the mats available
        to the human player and if so generate the corresponding play:
            - hand card => 'PUT', <index of card>   (SWAPPING_CARDS)
            - hand card => 'HAND', <index of card>  (PLAY_GAME)
            - hand card => 'SHOW', <index of card>  (FIND_STARTER)
            - face up table card => 'GET', <index of card>  (SWAPPING_CARDS)
            - face up table card => 'FUP', <index of card>  (PLAY_GAME)
            - face down table card => 'FDOWN', <index of card>
            - talon => 'REFILL'
            - discard pile => 'TAKE'
                           or 'KILL' (if >= 4 cards of same rank at the top)
            - end turn button => 'END'
            - quit button => 'QUIT'
            - everywhere else => play = None
        We set this play (or None) as selected play of the human player
        (players[0]).
        Note, that we still have to check in the 'select_play()' methode of
        HumanPlayer, if this is a legal play.

        If it's not the human player's turn, a mouse click everywhere, will
        reset the 'waiting_for_human' flag as an acknowledge from the human
        player for the last opponent action.

        :param x:               X-coord of mouse when button was pressed.
        :type x:                float
        :param y:               Y-coord of mouse when button was pressed.
        :type y:                float
        :param button:          the mouse button which was pressed.
        :type button:           int
        :param modifiers:       key modifiers (SHIFT, ALT, etc.)
        :type modifiers:        int
        """
        # reset the tips in the message window
        self.tips = ['', '', '']

        # reset the 'wait_for_human' flag
        self.wait_for_human = False

        # check if the game is over
        if self.state.game_phase == SHITHEAD_FOUND:
            return  # nothing more to do

        # check if the human player is still in the game
        if not isinstance(self.state.players[0], plr.HumanPlayer):
            return  # nothing more to do

        # get list of cards we clicked on
        cards = arcade.get_sprites_at_point((x, y), self.card_list)

        # have we clicked on a card?
        if len(cards) > 0:
            top_card = cards[-1]
            play = self.get_human_play(top_card)
        else:
            # check if we have pressed the button
            mats = arcade.get_sprites_at_point((x, y), self.mat_list)
            if len(mats) > 0 and mats[0] == self.button:
                # load the pressed button image into the sprite
                self.press_button()
                play = Play('END')
            else:
                play = None

        # the human player is still in the game, is the current player
        # and has selected a play
        if self.state.player == 0 and play:
            # set this play as selected play
            self.state.players[0].set_clicked_play(play)
        else:
            # not the human player's turn
            # => reset selected play to None
            self.state.players[0].set_clicked_play(None)

    def pull_to_top(self, card: arcade.Sprite):
        """
        Pull card to top of rendering order (last to render, looks on-top.
        """
        # remove, and append to the end
        self.card_list.remove(card)
        self.card_list.append(card)

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
        :param modifiers:       Key modifiers (SHIFT, ALT, etc.)
        :type modifiers:        int
        """
        # load the released button image into the sprite
        self.release_button()

    def get_tips(self, play, rank):
        """
        Get up to 3 lines of tips for the specified play.

        :param play:    Play corresponding to mouse position.
        :type play:     Play
        :param rank:    rank of card under mouse.
        :type rank:     str
        :return:        3 lines of tips.
        :rtype:         list
        """
        tips = ['', '', '']
        if play:
            legal_plays = self.state.get_legal_plays()
            # turn into a list of strings
            legal_plays = [str(p) for p in legal_plays]
            # check selected play is legal
            if str(play) in legal_plays:
                tips[0] = self.tips_dict[play.action]
                if play.action == 'HAND' or play.action == 'FUP':
                    tips[1] = self.tips_dict[rank]

        return tips

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Mouse moved event callback function.

        This function is called when the mouse was moved.

        :param x:       X-coord of mouse.
        :type x:        float
        :param y:       Y-coord of mouse.
        :type y:        float
        :param dx:      change in X-coord.
        :type dx:       float
        :param dy:      change in y-coord.
        :type dy:       float
        """
        # only show tips while in the game phase
        if self.state.game_phase != PLAY_GAME:
            return  # nothing more to do

        # check if the human player is still in the game
        if not isinstance(self.state.players[0], plr.HumanPlayer):
            return  # nothing more to do

        # Not the human player's turn
        if self.state.player != 0:
            return  # nothing more to do

        # is the mouse hovering over a card
        cards = arcade.get_sprites_at_point((x, y), self.card_list)
        if len(cards) > 0:
            top_card = cards[-1]
            play = self.get_human_play(top_card)
            rank = top_card.card.rank
        else:
            # check if the mouse is over the 'DONE' button
            mats = arcade.get_sprites_at_point((x, y), self.mat_list)
            if len(mats) > 0 and mats[0] == self.button:
                play = Play('END')
                rank = None
            else:
                play = None
                rank = None
        self.tips = self.get_tips(play, rank)

    def update_discard_pile(self):
        """
        Update the discard pile.

        Checks if there's a mismatch between the discard pile on the gui
        (sprites) and the discard pile in the game state.
        There are 3 possibilities to have a mismatch between the displayed
        discard pile (sprites) and the discard pile in the game state:
           1. The previous player has legally played a '10', i.e. in the new
              game state the discard pile has already been killed.
           2. The previous player has blindly played a face down table card
              which doesn't fit the discard pile (e.g. a '10' on a '7') and in
              the new game state all discard pile cards are already on this
              player's hand.
           3. The previous player has played his last card and is out now, but
              where are 4 or more cards of same rank at the top of the discard
              pile (no 'KILL' play by current player).

        In case of a mismatch, we have to find out where the card belonging to
        the sprite at the top of the discard pile is now in the game state
        (removed cards pile or player) and program the card mover to move all
        sprites from the discard pile to the found place.

        TODO handle the case where a player is OUT and now where are 4 or more
             cards with same rank at the top of the discard pile, i.e. the
             player cannot kill the discard pile himself because he's already
             out.

        :return:    True => wait for discard pile to be moved
                    False => no discard pile movement, continue
        :rtype:     bool
        """
        # get the card sprites in the discard pile
        disc = self.mover.places['discard'].cards[0]

        # check if there's a mismatch between gui and game state
        if len(disc) > 0 and len(self.state.discard) == 0:
            # get the top card of the (GUI) discard pile
            card_sprite = disc[-1]
            if card_sprite.card in self.state.killed:
                # game state has this card in the removed cards pile
                # => program mover to move discard pile to removed cards
                for i, card_sprite in enumerate(disc[::-1]):
                    # add discard pile cards in reversed order to mover list
                    self.mover.add(
                        card_sprite, 'removed', 0, 1 + i * KILL_DELAY, False)
                self.mover.start()
                return True

            # otherwise, find the player, who has this card on his hand
            for i, player in enumerate(self.state.players):
                if card_sprite.card in player.hand:
                    break
            else:
                raise ValueError("Cannot find player who took discard pile"
                                 " after playing face down card"
                                 f" {card_sprite.card}!")

            # program the card mover to move the discard pile to the hand of
            # the found player
            for i, card_sprite in enumerate(disc[::-1]):
                # add discard pile cards in reversed order to mover list
                self.mover.add(
                    card_sprite, player.name, 3, 1 + i * TAKE_DELAY, False)
            self.mover.start()
            return True

        elif self.state.n_played == 0 and self.state.discard.get_ntop() >= 4:
            # at the start of a player's round there are 4 or more cards with
            # same rank on top of the discard pile.
            # this is possible if the previous player went out playing his last
            #  card on the discard pile (i.e. hadn't the option to select the
            # 'KILL' play)
            # => kill the discard pile in current state without using a play
            for i in range(len(self.state.discard)):
                card = self.state.discard.pop_card()
                self.state.killed.add_card(card)
            # and move the discard pile to the removed cards pile in the gui
            for i, card_sprite in enumerate(disc[::-1]):
                # add discard pile cards in reversed order to mover list
                self.mover.add(
                    card_sprite, 'removed', 0, 1 + i * KILL_DELAY, False)
            self.mover.start()
            return True

        else:
            # nothing to do.
            return False

    def update_message_window(self):
        """
        Update message in message window according to game phase.

        Creates messages according to game phase with turn number, player name
        and '...' animation.
        """

        # get number of players
        n_players = len(self.state.players)
        # get the current player
        player = self.state.players[self.state.player]
        # is this the human player
        human = isinstance(player, plr.HumanPlayer)
        # get game phase
        phase = self.state.game_phase
        # get the turn count
        turn_count = self.state.turn_count

        # print instructions in message window
        if phase == SWAPPING_CARDS:
            if human:
                # instruction for human player
                self.set_message('MAY_SWAP', 0, player.name)
            else:
                # commenting on AI players
                self.set_message('IS_SWAPPING', 0, player.name)

        elif phase == PLAY_GAME:
            if self.state.next_direction:
                pdir = '\u21bb'      # clockwise
            else:
                pdir = '\u21ba'      # counterclockwise
            thinking = self.thinking[int(self.thinking_cnt / 20) % 4]
            self.set_message('TURN_NAME', turn_count, player.name, thinking,
                             pdir=pdir, tips=self.tips)
            if turn_count == 1:
                # very 1st turn
                # => make sure all shown AI player cards are face down again
                for i in range(1, n_players):
                    self.mover.hide_hand_cards(self.state.players[i].name)

        elif phase == SHITHEAD_FOUND and self.shithead is None:
            self.set_message('IS_SHITHEAD', 0, player.name)
            # update shithead's statistics
            self.stats.update(player.name, 0, player.turn_count)
            self.stats.print()
            self.shithead = player.name
            self.wait_for_human = True

        elif phase == ABORTED and not self.aborted:
            self.set_message('GAME_ABORTED', turn_count)
            # update statistics
            # revert statistics of all players which are already out.
            rslt = Game.get_result(self.state)
            for name in rslt.keys():
                if rslt[name][0] != 0:  # player has already scored
                    score = rslt[name][0]
                    turn_count = rslt[name][1]
                    self.stats.revert(name, score, turn_count)
            self.stats.print()
            self.aborted = True
            self.wait_for_human = True

    def get_play(self):
        """
        Get play from player.

        If the current player is the human player during the starter auction,
        'END' is returned automatically if he cannot show the starting card.
        Otherwise, we just ask the current player to give us his next play.
        In case of the human player we have to wait for a mouse click on a
        place, which results in a legal play. As long as the human player has
        not made a valid choice we immediatly return None.
        The AI player usually immediately answers with a valid play, but
        DeepShit and DeeperShit may start a thread to find the best play.
        In this case it's also possible, that None is returned if
        DeepShit/DeeperShit is not ready yet.

        :return:    legal play, None => not ready yet.
        :rtype:     Play
        """
        # get the current player
        player = self.state.players[self.state.player]
        # is this the human player
        human = isinstance(player, plr.HumanPlayer)
        # get game phase
        phase = self.state.game_phase

        # skip human player during starter auction if he cannot show the card
        if human and phase == FIND_STARTER:
            # check if human player can show the starter card
            if len(self.state.get_legal_plays()) > 1:
                # instruction for human player
                suit = STARTING_SUITS[self.state.starting_card % 4]
                rank = STARTING_RANKS[self.state.starting_card // 4]
                card = Card(0, suit, rank)
                self.set_message('SHOW_OR_SKIP', 0, player.name, '', card)
                # human player decides interactively
                return player.play(self.state)
            else:
                # human player cannot show card
                return Play('END')
        else:
            # let the current player play one action
            # human player => mouse interaction
            return player.play(self.state)

    def apply_play(self, play):
        """
        Apply the play returned by the current player to the game screen.

        If a play has been selected by the current player:
            - reset the '...' animation.
            - program the card mover to show the selected play.
            - get the new game state by applying this play to the old game
              state.
            - log the selected play.
            - if the FIND_STARTER phase has ended display a message.
            - start the mover to execute the programmed card moves.
        Otherwise (None returned by player): just update the '...' animation.

        :param play:    play selected by current player.
        :type play:     Play
        """
        # get game phase
        phase = self.state.game_phase

        # shithead found or game aborted => nothing to do
        if phase == SHITHEAD_FOUND or phase == 'ABORTED':
            return

        if play:
            # legal play returned by player =>  reset '...' animation counter
            self.thinking_cnt = 0

            # program card mover to move cards according to this play
            self.show_play(play)

            # apply this  play to the current state to get to the next state
            # NOTE fup_table is only needed for fup_table generation
            self.state = Game.next_state(self.state, play, None, self.stats)

            # log this play
            self.state.print()

            # check the result of the starting player auction
            if phase == FIND_STARTER and self.state.game_phase == PLAY_GAME:
                # starting player has been found (not same as current player!)
                starter = self.state.players[self.state.player]
                self.set_message('IS_STARTER', 0, starter.name)
                self.wait_for_human = True

            # start moving cards
            self.mover.start()
        else:
            # None returned by current player
            # => select_play thread has not finished yet
            #    or human player has not selected a legal play
            #    => we display the "thinking..." animation.
            self.thinking_cnt += 1

    def on_update(self, delta_time):
        """
        Game update callback function.

        This function is called about 60 times per second by the game loop.
        This is where all of the game logic should be placed.
        We first wait for the card mover to finish moving cards around.
        As a result of the previous play it may be necessary to move the
        discard pile either to the previous player's hand or to the removed
        cards pile.
        The message window is updated according to the current game phase.
        If the game is finished, i.e. a shithead has been found, we update the
        counters in the player configuration with the statistic counters and
        save it to the config file.
        Setup the result screen with the current statistics (and shithead) and
        make it the active view.
        If no shithead has been found yet, ask the current player for his next
        play and program the card mover to move the corresponding cards, before
        we apply the chosen play to the current game state, to get the next
        game state.
        The human player (or DeepShit waiting for its simulation thread to
        finish) may return None instead of a play, i.e. the human player hasn't
        made a valid selection yet (clicked on a card or button corresponding
        to a legal play for the current game state). In this case
        we do nothing (displaying the '...' animation), waiting for the human
        player to make a selection.

        :param delta_time:  time since last execution of on_update().
        :type delta_time:   float.
        """
        # if a wait time has been set decrement it
        if self.wait_time > 0:
            self.wait_time -= delta_time

        # move cards, if necessary
        if self.mover.update(delta_time) or self.wait_time > 0:
            # wait till card moving is finished
            return

        # reset the 'dealing' flag
        self.dealing = False

        # if the discard pile has been killed by playing a '10' or has been
        # taken by playing a face down table card, the discard pile has now to
        # be moved to the removed cards pile or the player's hand.
        if self.update_discard_pile():
            return  # wait for card mover to move the discard pile

        # wait for human player to click anywhere
        # but game is neither finished nor aborted
        if self.wait_for_human and self.shithead is None and not self.aborted:
            self.message.set_line(4, 'click anywhere to continue')
            return

        # update message window according to game phase
        # Shithead found => update stats of Shithead, set the 'shithead' flag
        # Game aborted => revert stats and set the 'aborted' flag
        self.update_message_window()

        # shithead found or game aborted => show result
        if self.shithead or self.aborted:
            if self.wait_for_human:
                self.message.set_line(4, 'click anywhere to continue')
                return

            # update the player counters in the configuration
            for i, player in enumerate(self.config['players']):
                name, ptype, counters = player
                if ptype != '---':
                    counters = self.stats.get_stats(name)
                    self.config['players'][i] = (name, ptype, counters)
            # save updated configuration to file
            filename = self.config['config_file']
            with open(filename, 'w', encoding='utf-8') as json_file:
                json.dump(self.config, json_file, indent=4)

            #  create the result screen view
            result_view = result.ResultView()
            # setup the result view (with original players list)
            result_view.setup(self.stats, self.shithead, self.config)
            # and switch to the result view
            self.window.show_view(result_view)
            # !!! NOTE !!!
            # on_update() will be completed before we change to the result
            # view, i.e. without the return another play will be applied
            # although the game is already over. If DeeperShit is the Shithead
            # this would start a new MCTS thread, which will never be properly
            # terminated and will cause the GUI to slow down and come to a
            # grinding halt.
            return

        # get player's next play and apply it to the game state
        self.apply_play(self.get_play())


def main():
    """
    Tests for gui module.
    """


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
