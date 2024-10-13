'''
Discard class for Shithead game.

The Discard class is a shithead specific sub-class of Deck.
While Card and Deck could be used for any other card game, Discard has some
additional methods which can only be used for the shithead game.

23.08.2022  Wolfgang Trachsler
'''

# local imports (modules in same package)
from .cards import Card, Deck, CARD_RANKS

# This table gives for every rank at the top of the discard pile (key) a list
# of cards which can be played on top of it.
# The 1st card added to the discard pile by a player during his turn has to be
# of a rank equal or higher to the rank of the card on top of the discard pile.
# If the top card is a '3' (transparent) it must be equal or higher than the
# 1st non-'3' card below the top.
# '2' and '3' can be played on everything.
# '10' can be played on everything except '7'.
# If a '7' is at the top or the 1st card below one or more '3's, only cards
# with ranks equal or lower than '7' may be played.
# Everything can be played on an empty discard pile.
# There's never a '10' on top of the discard pile (kills the pile).
# A 'Q' can only be at the top of the discard pile, if it was the very last
# card of a player, because otherwise it must be covered by the same player
# with any card (or if this player played a '3' to cover the queen).
# After a player could play the 1st card in his turn on the discard pile, he
# may now play more cards of the same rank, or any card after a 'Q'.
ACCEPT_TABLE = [
    ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],  # '2'
    ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],  # '3'
    ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],  # '4'
    ['2', '3', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],       # '5'
    ['2', '3', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'],            # '6'
    ['2', '3', '4', '5', '6', '7'],                                      # '7'
    ['2', '3', '8', '9', '10', 'J', 'Q', 'K', 'A'],                      # '8'
    ['2', '3', '9', '10', 'J', 'Q', 'K', 'A'],                           # '9'
    [],  # '10' (kills the pile => never happens)                         '10'
    ['2', '3', '10', 'J', 'Q', 'K', 'A'],                                # 'J'
    ['2', '3', '10', 'Q', 'K', 'A'],  # 'Q' (played by previous player!)   'Q'
    ['2', '3', '10', 'K', 'A'],                                          # 'K'
    ['2', '3', '10', 'A'],                                               # 'A'
]


# ----------------------------------------------------------------------------
class Discard(Deck):
    '''
    Class representing the discard pile of a shithead game.

    Players add cards on top of the discard pile.
    A player who cannot play a card on top of the discard pile has to take all
    cards from discard pile into his hand.
    The discard pile is killed, i.e. all its cards are removed from the game,
    after a '10' has been played on top of it, or if 4 or more cards of the
    same rank are on its top.
    '3's are considered to be transparent, i.e. when playing a card on top of
    the discard pile, the 1st non-3 card at its top determines which cards can
    be played (only '3's in pile => any card can be played).
    '''
    def __init__(self):
        '''
        Create an empty discard pile.
        '''
        super().__init__()
        self.deck = []

    def get_top_rank(self):
        '''
        Get rank of card at top of discard pile.

        :return: rank of top card, None => discard pile empty
        :rtype: str
        '''
        if len(self.deck) > 0:
            return self.deck[-1].rank
        else:
            return None     # discard pile empty

    def get_top_non3_rank(self):
        '''
        Get rank of 1st card from top of discard pile which is not a '3'.

        :return: rank of 1st non-3 card, None => pile empty or only '3's
        :rtype: str
        '''
        for card in self.deck[::-1]:
            # go through discard pile in reversedorder.
            if card.rank != '3':
                return card.rank
        # if we get here => only '3' or empty discard pile
        return None

    def get_ntop(self):
        '''
        Get number of cards with same rank at top.

        :return: number of cards with same rank at top of discard pile.
        :rtype: int
        '''
        ntop = 0
        top_rank = self.get_top_rank()
        # count cards with same rank at the top
        for card in self.deck[::-1]:
            # go through discard pile in reversed order.
            if card.rank == top_rank:
                ntop += 1   # same rank => increment count
            else:
                break  # 1st different rank below top
        return ntop

    def get_ntop_visible(self):
        '''
        Get number of visible cards at the top of the discard pile.

        Usually, it's just the number of cards with same rank at the top of the
        discard pile, but if there are '3's at the top and if they are not the
        only cards in the discard pile, the 1st card below the '3's is also
        visible.

        :return:    number of visible cards at the top of the discard pile.
        :rtype:     int
        '''
        nof_visible = self.get_ntop()
        if (self.get_top_rank() == '3'
                and self.get_top_non3_rank() is not None):
            nof_visible += 1
        return nof_visible

    def get_top_string(self, score=None, show_all=False):
        '''
        get a string representation of top discard pile.

        If all has been set to True, add all cards in the discard pile.
        Otherwise, just add all cards with same rank at the top of the
        discard pile. If one or more '3's are at top of the discard pile,
        also add the 1st non-3 card.

        :param score:   average value of cards in pile.
        :type all:      float
        :param all:     True => print all cards in the discard pile.
        :type all:      bool
        :return:        string representation of discard pile
        :rtype:         str
        '''
        if show_all:
            # print all cards in discard pile
            discard_str = ' '.join([str(card) for card in self.deck])
            if score is not None:
                # print all cards in discard pile and their average value
                discard_str = f"{discard_str}   {score:.1f}"
        else:
            # just print all cards with same rank at top
            discard_str = (
                ' '.join([str(card)
                          for card in self.deck[-self.get_ntop_visible():]]))
        return discard_str

    def print_top(self, score=None, show_all=False):
        '''
        Print cards in discard pile.

        If all has been set to True, print all cards in the discard pile.
        Otherwise, just print all cards with same rank at the top of the
        discard pile. If one or more '3's are at top of the discard pile,
        also print the 1st non-3 card.

        :param score: average value of cards in pile.
        :type all: float
        :param all: True => print all cards in the discard pile.
        :type all: bool
        '''
        print(self.get_top_string(score, show_all))

    def copy(self):
        '''
        Creates a copy of itself.

        Creates a new empty Discard object and then copies all cards from the
        original discard and adds them to the new discard.

        :return:            copy of original discard (not just reference)
        :rtype:             Discard
        '''
        new_discard = Discard()
        for card in self.deck:
            new_discard.add_card(card.copy())
        return new_discard

    def check(self, first, card):
        '''
        Checks if a card can be played on the discard pile.

        :param first:   True => player first play this turn.
        :type first:    bool
        :param card:    card which shall be played.
        :type card:     Card
        :return:        True => can be played, False => cannot be played.
        :rtype:         bool
        '''
        # pile is empty => any card can be played
        #                  (also if it's not the 1st card this turn).
        if len(self.deck) == 0:
            return True

        # pile is not empty and it's player's 1st card this turn
        if first:
            # pile is not empty => check against top non-3 card in discard pile
            ref = self.get_top_non3_rank()
            if ref is None:
                # only '3's in discard pile => any card can be played
                return True
            # check if the specified card can be played on the reference rank
            ref_idx = CARD_RANKS.index(ref)
            if card.rank in ACCEPT_TABLE[ref_idx]:
                return True
            else:
                return False
        # pile is not empty and player has already played card(s) this turn
        # => card may be played if a 'Q' is at the top (but only less than 4
        #    'Q', otherwise we had to kill the discard pile first!) or if it
        #    has the same rank as the top card.
        else:
            top = self.get_top_rank()
            if top == 'Q' and self.get_ntop() < 4:
                # any card can be played on 1 - 3 'Q's, but only another 'Q'
                # on 4 or more 'Q's
                return True
            elif card.rank == top:
                # card with same rank as top card can be played.
                return True
            else:
                return False


def test_discard_pile():
    """
    Test for discard pile methods.
    """
    print('-----------------------------------------------------------------')
    print('Test discard pile get_top_rank() method ')
    discard = Discard()
    card = Card(0, 'Clubs', '4')
    print(f'check if {card} can be added to empty discard pile')
    print(discard.check(True, card))
    discard.add_card(card)
    discard.print_top()
    print(f'top rank: {discard.get_top_rank()}')
    card = Card(0, 'Spades', '5')
    print(f'check if {card} could be added as follow up card')
    print(discard.check(False, card))
    card = Card(0, 'Spades', '4')
    print(f'check if {card} could be added as follow up card')
    print(discard.check(False, card))
    discard.add_card(card)
    discard.print_top()
    print(f'number of cards with same rank at the top: {discard.get_ntop()}')
    card = Card(0, 'Hearts', '7')
    print(f'check if {card} can be added to discard pile')
    print(discard.check(True, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Hearts', 'A')
    print(f'check if {card} can be added to discard pile')
    print(discard.check(True, card))
    card = Card(0, 'Diamonds', '5')
    print(f'check if {card} can be added to discard pile')
    print(discard.check(True, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Hearts', 'Q')
    print(f'check if {card} can be added to discard pile')
    print(discard.check(True, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Clubs', '7')
    print(f'check if {card} can be added to discard pile as follow up card')
    print(discard.check(False, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Spades', '7')
    print(f'check if {card} can be added to discard pile as follow up card')
    print(discard.check(False, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Spades', '3')
    print(f'check if {card} can be added to discard pile')
    print(discard.check(True, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Hearts', '3')
    print(f'check if {card} can be added to discard pile as follow up card')
    print(discard.check(False, card))
    discard.add_card(card)
    discard.print_top()
    card = Card(0, 'Spades', '10')
    print(f'check if {card} can be added to discard pile')
    print(discard.check(True, card))
    print(f'top rank: {discard.get_top_rank()}')
    print(f'number of cards with same rank at the top: {discard.get_ntop()}')
    print(f'top non-3 rank at the top: {discard.get_top_non3_rank()}')


if __name__ == '__main__':
    test_discard_pile()
