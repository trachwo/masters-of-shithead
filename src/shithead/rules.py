"""
Screen with shithead rules.

Arcade view for displaying the shithead rules.
All titles, sub-titles, and sections of the rule page are created as arcade text objects.
The content of these text objects is loaded from a json-file with either
English or German text.
The rule page has a main title at the top with a short introduction into the
game filling the width of the page.
The detailed rules are structured as sub-sections headed by smaller titles and
arranged in two columns below the introduction.
Using text objects allows us to calculate the vertial position of a sub-section,
even if the size of the sub-sections differs for different languages.
The rule page is opened as subprocess (Popen) from the shithead starting page
and exists independently from the actual game screen until it is closed by the
user.

22.04.2023 Wolfgang Trachsler
"""



import arcade
import json
import argparse
import os

# Screen title and size
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
SCREEN_TITLE = "Sh*thead"

DEFAULT_LINE_HEIGHT = 18
DEFAULT_FONT_SIZE = 12
COLOR = arcade.color.BLACK
FONT = 'Times New Roman'

class RulesView(arcade.View):
    '''
    View where we show the rules of the shithead game.
    '''

    def __init__(self, filename):
        '''
        Initializer.

        Loads the rule strings from the specified JSON file into a dictionary.

        :param filename:    name of json file with rule strings.
        :type filename:     str
        '''

        super().__init__()

        self.rules = None
        try:
            with open(filename, 'r') as json_file:
                self.rules = json.load(json_file)
        except OSError as exception:
            print(f"### Warning: couldn't load rules from file {filename}")
            return

        # set the background color to beige.
        arcade.set_background_color(arcade.color.BEIGE)

        # create text list
        self.text_list = []

        # create the main title text object
        start_x = 0
        start_y = SCREEN_HEIGHT - DEFAULT_LINE_HEIGHT * 2.5
        text = arcade.Text(self.rules['main_title'], start_x, start_y,
                arcade.color.CINNABAR, DEFAULT_FONT_SIZE * 2, font_name=FONT,
                width=SCREEN_WIDTH, align='center')
        self.text_list.append(text)

        # create the intro text object
        start_x = 20
        start_y = text.bottom - DEFAULT_LINE_HEIGHT * 2
        text = arcade.Text(self.rules['intro'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=984)
        self.text_list.append(text)

        # --- left column ---
        # create the Preparation text objects
        start_x = 0
        start_y = text.bottom - DEFAULT_LINE_HEIGHT * 2
        text = arcade.Text(self.rules['prep']['title'], start_x, start_y,
                arcade.color.CINNABAR, DEFAULT_FONT_SIZE, font_name=FONT,
                width=512, align='center', bold=True)
        self.text_list.append(text)
        start_x = 20
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['prep']['text'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=472)
        self.text_list.append(text)

        # create the Gameplay text objects
        start_x = 0
        start_y = text.bottom - DEFAULT_LINE_HEIGHT * 2
        text = arcade.Text(self.rules['play']['title'], start_x, start_y,
                arcade.color.CINNABAR, DEFAULT_FONT_SIZE, font_name=FONT,
                width=512, align='center', bold=True)
        self.text_list.append(text)
        start_x = 20
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['play']['text'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=472)
        self.text_list.append(text)

        # --- right column ---
        # create the text objects for playing cards rules
        start_x = 512
        # below intro
        start_y = self.text_list[1].bottom - DEFAULT_LINE_HEIGHT * 2
        text = arcade.Text(self.rules['cards']['title'], start_x, start_y,
                arcade.color.CINNABAR, DEFAULT_FONT_SIZE, font_name=FONT,
                width=512, align='center', bold=True)
        self.text_list.append(text)
        start_x = 552
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text1'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text2'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text3'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text4'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text5'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text6'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text('-', start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['cards']['text7'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)

        # create text objects for special cards
        start_x = 512
        start_y = text.bottom - DEFAULT_LINE_HEIGHT * 2
        text = arcade.Text(self.rules['special']['title'], start_x, start_y,
                arcade.color.CINNABAR, DEFAULT_FONT_SIZE, font_name=FONT,
                width=512, align='center', bold=True)
        self.text_list.append(text)
        start_x = 552
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card1'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text1'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card2'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text2'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card3'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text3'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card4'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text4'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card5'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text5'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card6'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text6'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)
        start_y = text.bottom - DEFAULT_LINE_HEIGHT
        text = arcade.Text(self.rules['special']['card7'], start_x-20, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT, bold=True)
        self.text_list.append(text)
        text = arcade.Text(self.rules['special']['text7'], start_x, start_y,
                COLOR, DEFAULT_FONT_SIZE, font_name=FONT,
                multiline=True, width=452)
        self.text_list.append(text)

    def setup(self):
        pass

    def on_draw(self):
        """
        Render the screen callback function.

        This function is called approximately 60 times per second by the game
        loop (-> arcade.run()) to redraw the screen.
        """
        # clear the screen
        self.clear()

        # main title
        for text in self.text_list:
            text.draw()


def main():
    # command line parser
    parser = argparse.ArgumentParser()
    # add positional argument filename
    parser.add_argument('filename')
    # parse the command line to get the filename
    args = parser.parse_args()
    print(f"### {args.filename}")

    # testing the config view
    # open a window with predefined size and title
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

    # create a RulesView with texts from the specified file
    rules_view = RulesView(args.filename)
    # and make it the view shown in the window
    window.show_view(rules_view)
    # setup the rules view
    rules_view.setup()

    # start
    arcade.run()

if __name__ == "__main__":
    main()
