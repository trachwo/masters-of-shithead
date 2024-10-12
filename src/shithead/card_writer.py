"""
Making Big Letters with Cards.
"""
import json
import argparse

import arcade

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Write Title with Cards"

# Constants for sizing
CARD_SCALE = 0.6

# How big are the cards?
CARD_WIDTH = 140 * CARD_SCALE
CARD_HEIGHT = 190 * CARD_SCALE

# How big is the mat we'll place the card on?
MAT_PERCENT_OVERSIZE = 1.25
MAT_HEIGHT = int(CARD_HEIGHT * MAT_PERCENT_OVERSIZE)
MAT_WIDTH = int(CARD_WIDTH * MAT_PERCENT_OVERSIZE)

# How much space do we leave as a gap between the mats?
# Done as a percent of the mat size.
VERTICAL_MARGIN_PERCENT = 0.10
HORIZONTAL_MARGIN_PERCENT = 0.10

# The Y of the bottom row (2 piles)
BOTTOM_Y = MAT_HEIGHT / 2 + MAT_HEIGHT * VERTICAL_MARGIN_PERCENT

# The X of where to start putting things on the left side
START_X = MAT_WIDTH / 2 + MAT_WIDTH * HORIZONTAL_MARGIN_PERCENT

# y-coord of title template => taken from start.py
TITLE_Y = 535

# Card constants
CARD_VALUES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q",
               "K"]
CARD_SUITS = ["Clubs", "Hearts", "Spades", "Diamonds"]

DEFAULT_LINE_HEIGHT = 18
DEFAULT_FONT_SIZE = 12


class Card(arcade.Sprite):
    """ Card sprite """

    def __init__(self, suit, value, scale=1):
        """ Card constructor """

        # Attributes for suit and value
        self.suit = suit
        self.value = value

        # Image to use for the sprite when face up
        self.image_file_name = (f":resources:images/cards/card{self.suit}"
                                f"{self.value}.png")

        # Call the parent
        super().__init__(self.image_file_name, scale, hit_box_algorithm="None")


class CardWriter(arcade.Window):
    """ Main application class. """

    def __init__(self, letter, title, size):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Sprite list with all the cards already in the title.
        self.card_list = arcade.SpriteList()
        # Sprite list with all cards of one letter
        self.letter_cards = arcade.SpriteList()
        # normalized coords of cards in one letter
        self.letter_coords = []
        # minimum coords of letter, to get the actual card coords the
        # normalized coords are added to these minimum coords
        self.letter_coords_min = (0, 0)
        # letter template (only one letter)
        self.letter = letter[0]
        # Title template (several letters)
        self.title = title
        self.title_size = size
        # list of text objects
        self.text_list = []
        # current coordinates of mouse pointer
        self.mouse_coords = (0, 0)
        # letter loaded flag
        # False => move single card, True => move all cards of a letter
        self.letter_loaded = False
        # List of cards we are dragging with the mouse
        self.held_cards = []
        # scale down cards in letter by this ratio
        self.ratio = 0.5
        # symbol read from keyboard
        self.key_buffer = None

        # set the background color
        arcade.set_background_color(arcade.color.AMAZON)

        # create the letter template text object
        start_x = 10
        start_y = SCREEN_HEIGHT - DEFAULT_LINE_HEIGHT * 40
        text = arcade.Text(self.letter, start_x, start_y,
                           arcade.color.CINNABAR, DEFAULT_FONT_SIZE * 48,
                           width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

        # create the main title text object
        start_x = 0
        start_y = TITLE_Y
        text = arcade.Text(self.title, start_x, start_y,
                           arcade.color.CINNABAR,
                           DEFAULT_FONT_SIZE * self.title_size,
                           width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

    def pull_to_top(self, card: arcade.Sprite):
        """
        Pull card to top of rendering order (last to render, looks on-top)
        """
        # Remove, and append to the end
        self.letter_cards.remove(card)
        self.letter_cards.append(card)

    def store_letter(self):
        """
        Store card coords to file.
        """
        for card in self.letter_cards:
            self.letter_coords.append((card.position[0], card.position[1],
                                       card.angle))
        x_min = min([c[0] for c in self.letter_coords])
        y_min = min([c[1] for c in self.letter_coords])

        # normalize the coordinates
        self.letter_coords = [(c[0] - x_min, c[1] - y_min,
                               c[2]) for c in self.letter_coords]
        print(self.letter_coords)
        # store normalized coords to file
        with open(f'letter_{self.letter}.json',
                  'w', encoding='utf-8') as json_file:
            json.dump(self.letter_coords, json_file, indent=4)
        self.letter_coords = []

    def load_letter(self, filename, x, y):
        """
        Load card coords from file.
        """
        try:
            with open(filename, 'r', encoding='utf-8') as json_file:
                self.letter_coords = json.load(json_file)
                print(self.letter_coords)
        except IOError as exception:
            print(f"### Warning couldn't load file: {exception}")
            return

        for coord in self.letter_coords:
            card = Card('Diamonds', '3', CARD_SCALE * self.ratio)
            card.position = (coord[0] * self.ratio + x,
                             coord[1] * self.ratio + y)
            card.angle = coord[2]
            self.letter_cards.append(card)

        self.letter_loaded = True

    def change_letter_size(self, change):
        """
        Change the letter size.
        """
        # find x_min and y_min for the current letter cards coordinates
        x_min = min([card.position[0] for card in self.letter_cards])
        y_min = min([card.position[1] for card in self.letter_cards])

        # change size and coords of cards according to ratio
        self.letter_cards = arcade.SpriteList()
        self.ratio *= change
        print(f'### ratio: {self.ratio}')
        for coord in self.letter_coords:
            card = Card('Diamonds', '3', CARD_SCALE * self.ratio)
            card.position = (coord[0] * self.ratio + x_min,
                             coord[1] * self.ratio + y_min)
            card.angle = coord[2]
            self.letter_cards.append(card)

    def on_draw(self):
        """ Render the screen. """
        # Clear the screen
        self.clear()

        # Draw the text
        for text in self.text_list:
            text.draw()

        # Draw the cards
        self.letter_cards.draw()
        self.card_list.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called when the user presses a mouse button. """

        # Get list of cards we've clicked on
        cards = arcade.get_sprites_at_point((x, y), self.letter_cards)

        # Have we clicked on a card?
        if len(cards) > 0:

            # Might be a stack of cards, get the top one
            primary_card = cards[-1]

            if self.letter_loaded:
                # after a letter has been loaded all cards are moved
                # simultaneously
                self.held_cards = [card for card in self.letter_cards]

            else:
                # All other cases, grab the face-up card we are clicking on
                self.held_cards = [primary_card]
                # Put on top in drawing order
                self.pull_to_top(self.held_cards[0])

    def on_mouse_release(self, x: float, y: float, button: int,
                         modifiers: int):
        """ Called when the user presses a mouse button. """

        # If we don't have any cards, who cares
        if len(self.held_cards) == 0:
            return

        # We are no longer holding cards
        self.held_cards = []

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """ User moves mouse """

        # store the current mouse position
        self.mouse_coords = (x, y)

        # If we are holding cards, move them with the mouse
        for card in self.held_cards:
            card.center_x += dx
            card.center_y += dy

    def on_key_press(self, symbol, modifiers):
        """
        Apply pressed key.
        """
        self.key_buffer = symbol
        if symbol == arcade.key.UP:
            if len(self.held_cards) > 0:
                self.held_cards[0].angle += 5
        elif symbol == arcade.key.DOWN:
            if len(self.held_cards) > 0:
                self.held_cards[0].angle -= 5
        if symbol == arcade.key.LEFT:
            if len(self.held_cards) > 0:
                self.held_cards[0].angle += 45
        elif symbol == arcade.key.RIGHT:
            if len(self.held_cards) > 0:
                self.held_cards[0].angle -= 45
        elif symbol == arcade.key.ENTER:
            self.store_letter()
        elif symbol == arcade.key.INSERT:
            card = Card('Diamonds', '3', CARD_SCALE)
            card.position = START_X, BOTTOM_Y
            self.letter_cards.append(card)
            self.pull_to_top(card)
        elif symbol == arcade.key.DELETE:
            # Get list of cards under mouse pointer
            cards = arcade.get_sprites_at_point(self.mouse_coords,
                                                self.letter_cards)
            # are there any cards under the mouse pointer?
            if len(cards) > 0:
                # Might be a stack of cards, get the top one
                primary_card = cards[-1]
                # and remove it from the card list
                self.letter_cards.remove(primary_card)
        elif symbol >= arcade.key.A and symbol <= arcade.key.Z:
            self.load_letter(f'letter_{chr(symbol-32)}.json', 367, 95.2)
        elif symbol == arcade.key.PAGEUP:
            self.change_letter_size(1.1)
        elif symbol == arcade.key.PAGEDOWN:
            self.change_letter_size(0.9)
        elif symbol == arcade.key.NUM_ENTER:
            # copy current letter to card list and reset the letter card list.
            for card in self.letter_cards:
                self.card_list.append(card)
                self.letter_cards = arcade.SpriteList()
        elif symbol == arcade.key.END:
            # save coords of cards in card list to file
            title_coords = [(card.position[0], card.position[1], card.angle)
                            for card in self.card_list]
            print(title_coords)
            with open('title.json', 'w', encoding='utf-8') as json_file:
                json.dump(title_coords, json_file, indent=4)


def main():
    """ Main function """
    parser = argparse.ArgumentParser(prog='card_writer')
    parser.add_argument('-l', '--letter', default=' ', action='store')
    parser.add_argument('-t', '--title', default=' ', action='store')
    parser.add_argument('-s', '--size', type=int, default=1, action='store')
    args = parser.parse_args()

#    window = CardWriter(args.letter, args.title, args.size)
    CardWriter(args.letter, args.title, args.size)
    arcade.run()


if __name__ == "__main__":
    main()
