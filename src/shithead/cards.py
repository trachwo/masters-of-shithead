"""
Cards for shithead game

06.10.2022 Wolfgang Trachsler
"""

import random
from functools import cmp_to_key

# card constants => sequence of ranks and suits for card comparison
CARD_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
CARD_SUITS = ['Clubs', 'Diamonds', 'Hearts', 'Spades']

#------------------------------------------------------------------------------
class Card():
    """
    Playing card sprite.
    """

    def __init__(self, id, suit, rank):
        '''
        Initialize a Card.

        The 'seen' flag allows us to locate a card which has been seen face up
        during the whole game, i.e. a player with good memory (or a strong AI)
        could remember for each card which was face up once during the game,
        where it is right now (e.g. taken by a player with the discard pile)

        :param id:      deck id => unique cards in multi-deck games.
        :type id:       int
        :param suit:    card suit
        :type suit:     str
        :param rank:    card rank
        :type rank:     str
        '''
        self.id = id
        self.suit = suit
        self.rank = rank
        self.seen = False       # True => card has been seen face up during game.
        self.shown = False      # True => shown during starting player auction
        self.is_face_up = False # True => card is face up right now

    def __str__(self):
        '''
        Render playing card as string.

        :return: string with rank and suit symbol (unicode).
        :rtype: str
        '''
        suits = {'Clubs': '\u2663', 'Diamonds': '\u2662', 'Hearts': '\u2661',
                 'Spades': '\u2660'}
        return f"{self.rank}{suits[self.suit]}"

    def __lt__(self, other):
        '''
        Check if this card is lesser than other card.

        Lesser than method used for sorting cards.

        :param other: other card against which we compare this card.
        :type other: Card
        :return: True => this card < other card.
        :rtype: bool
        '''
        if CARD_RANKS.index(self.rank) == CARD_RANKS.index(other.rank):
            # both cards have the same rank => compare suits
            return CARD_SUITS.index(self.suit) < CARD_SUITS.index(other.suit)
        else:
            # otherwise, just compare ranks
            return CARD_RANKS.index(self.rank) < CARD_RANKS.index(other.rank)

    @classmethod
    def cmp(cls, card1, card2):
        '''
        Compares 2 cards.

        Function passed to 'functools.cmp_to_key' function in order to sort a
        list of cards.

        :param card1: 1st card.
        :type card1: Card
        :param card2: 2nd card.
        :type card2: Card
        :return: -1 => card1 < card2, 0 => card1 == card2, 1 => card1 > card2.
        :rtype: int
        '''
        if card1 < card2:
            return -1
        elif card2 < card1:
            return 1
        else:
            return 0

    def copy(self):

        '''
        Create a copy of itself.

        Creates a new Card object and then copies all attribute values from the
        original card to the new card.

        :return:            copy of original card (not just reference)
        :rtype:             Card
        '''
        # create a new card with same id, suit, and rank
        new_card = Card(self.id, self.suit, self.rank)
        # copy the attributes
        new_card.seen = self.seen
        new_card.shown = self.shown
        new_card.is_face_up = self.is_face_up

        return new_card

    def get_state(self):
        '''
        Get card state.

        :return:    dictionary with all card attributes.
        :rtype:     dict
        '''
        # create the state dictionary
        state = {}
        # add attributes to dictionary
        state['id'] = self.id
        state['suit'] = self.suit
        state['rank'] = self.rank
        state['seen'] = self.seen
        state['shown'] = self.shown
        state['is_face_up'] = self.is_face_up
        return state

    def face_down(self):
        """
        Turn the card face down.
        """
        # reset the face up flag
        self.is_face_up = False

    def face_up(self):
        """
        Turn the card face up.
        """
        # set the face up flag
        self.is_face_up = True

    @property
    def is_face_down(self):
        """
        Check if card is face down.

        :return:    True => card is face down.
        :rtype:     bool
        """
        return not self.is_face_up


#------------------------------------------------------------------------------
class Deck:
    '''
    Class representing a deck of cards.

    In the Shithead game one or more decks are used as face down talon to
    refill the player's hands from.
    '''
    def __init__(self, id=0, empty=False):
        '''
        Create a deck of 52 cards.

        Decks are always created as single decks of 52 cards (TODO Jokers).
        Bigger decks are created by adding single decks together.

        :param id:      deck ID => unique cards over multiple decks.
        :type id:       int
        :param empty:   True => create deck without cards.
        :type empty:    bool
        '''
        self.deck = []  # init list for holding the cards of this deck
        if not empty:
            # create deck of 52 cards
            for suit in CARD_SUITS:
                for rank in CARD_RANKS:
                    card = Card(id, suit, rank)
                    self.deck.append(card)

    def __str__(self):
        '''
        Render deck of cards as string.

        Each cards are rendered with rank and suit symbol (unicode)
        and seperated with spaces.

        :return:    string with cards as rank and suit symbol.
        :rtype:     str
        '''
        return ' '.join([str(card) for card in self.deck])

    def __len__(self):
        '''
        Implements len() function for Deck objects.

        :return: number of cards in deck.
        :rtype: int
        '''
        return len(self.deck)

    def __add__(self, other):
        '''
        Implement '+' operator for Deck class.

        :param other:   Deck object to be added.
        :type other:    Deck
        :return:        deck containing the cards of both decks.
        :rtype:         Deck
        '''
        self.deck += other.deck
        return self

    def __getitem__(self, index):
        '''
        Returns card from Deck at index with '[]' operator.

        :param index:   index of card in Deck object.
        :type index:    int
        :return:        card at index.
        :rtype:         Card
        '''
        return self.deck[index]

    def __setitem__(self, index, card):
        '''
        Assigns card to Deck at index with '[]' operator.

        :param index:   index into card list of Deck object.
        :type index:    int
        :param card:    card to be stored at index in Deck object.
        :type card:     Card
        '''
        self.deck[index] = card

    def index(self, card):
        '''
        Returns index of specified card.

        :param card:    card in deck.
        :type card:     Card
        :return:        index of card in deck.
        :rtype:         int
        '''
        return self.deck.index(card)
    
    def find(self, searched):
        '''
        Find card specified by id, suit, and rank.

        Compares id, suit, and rank of the specified card to the cards in this
        deck and returns the index of the 1st matching card.

        :param searched:    searched for card.
        :type searched:     Card
        :return:            index of searched card in deck, -1 => not found.
        :rtype:             int
        '''
        for idx, card in enumerate(self.deck):
            if (card.id == searched.id and 
                card.suit == searched.suit and
                card.rank == searched.rank):
                return idx
        else:
            return -1

    def add_card(self, card):
        '''
        Add a card to the deck.

        :param card: card added to deck.
        :type card: Card.
        '''
        self.deck.append(card)

    def pop_card(self, index=None):
        '''
        Remove card at index from deck and return it.

        If index was not specified remove the top card.

        :param index:   index of card we want to remove.
        :type index:    int
        :return:        card from deck at index or top card.
        :rtype:         Card
        '''
        if index is None:
            return self.deck.pop()
        else:
            return self.deck.pop(index)

    def remove_card(self, card):
        '''
        Remove the specified card.

        Remove the card from the deck and return it.

        :param card:    selected card.
        :type card:     Card
        :return:        the 1st card in deck which matches suit/rank/id,
                        or Exception.
        :rtype:         Card
        '''
        for i in range(len(self.deck)):
            if (self.deck[i].suit == card.suit and self.deck[i].rank == card.rank and
                self.deck[i].id == card.id):
                return self.deck.pop(i)
        else:
            raise Exception(f'No card {Card.ranks[card.rank]}{Card.suits[card.suit]} in this deck!')

    def shuffle(self):
        '''
        Shuffle deck.
        '''
        random.shuffle(self.deck)

    def sort(self, reverse=False):
        '''
        Sort deck of cards.

        Passes 'Card.cmp' method to 'functools.cmp_to_key' function to sort he
        deck.
        :param reverse:     True => sort in reverse order (default)
        :type reverse:      bool
        '''
        self.deck.sort(key=cmp_to_key(Card.cmp), reverse=reverse)

    def get_nof_ranks(self):
        """
        Count number of different ranks in this deck.
        """
        # get a list of all ranks in this hand
        ranks = [card.rank for card in self.deck]
        # convert it to a set and return its length
        return len(set(ranks))

    def get_nof_cards(self, rank):
        """
        Count number of cards with specified rank.

        :param rank:    rank of cards to be counted.
        :type rank:     str
        :return:        number of cards with specified rank
        :rtype:         int
        """
        return len([card for card in self.deck if card.rank == rank])

    def get_string(self, face_up=True):
        '''
        Get a string representation with all cards on a single line.

        :param face_up:     True => print all cards face up
                            False => print only face up cards face up.
        :type face_up:      bool
        :return:            string representation of deck.
        :rtype:             str
        '''
        deck_str = ''       # empty deck string
        if face_up:
            # print all cards face up
            deck_str = ' '.join([str(card) for card in self.deck])
        else:
            # only print cards marked as face up face up.
            for card in self.deck:
                if card.is_face_up:
                    # print card face up
                    deck_str = ' '.join([deck_str, str(card)])
                else:
                    # print card face down
                    deck_str = ' '.join([deck_str, 'XX'])
        return deck_str

    def print(self, face_up=True, end='\n'):
        '''
        Print all cards on a single line.

        :param face_up:     True => print all cards face up
                            False => print only face up cards face up.
        :type face_up:      bool
        '''
        print(self.get_string(face_up), end=end)
        deck_str = ''       # empty deck string

    def copy(self):
        '''
        Creates a copy of itself.

        Creates a new empty Deck object and then copies all cards from the
        original deck and adds them to the new deck.

        :return:            copy of original deck (not just reference)
        :rtype:             Deck
        '''
        new_deck = Deck(empty=True)     # id is doesn't matter for empty Deck
        for card in self.deck:
            new_deck.add_card(card.copy())

        return new_deck

    def get_state(self):
        '''
        Get deck state.

        :return:    list with all cards (states) in this deck.
        :rtype:     list
        '''
        # create the state list
        state = []
        for card in self.deck:
            state.append(card.get_state())
        return state

    def load_from_state(self, state, reset=True):
        '''
        Loads deck from state.

        This is used when recreating a game state from a log-file created
        with log-level 'Debugging'.

        :param state:   list with all cards (states) in this deck.
        :type state:    list
        :param reset:   reset deck before loading cards.
        :type reset:    bool
        '''
        if reset:
            # reset the card list of this deck
            self.deck = []
        # create cards from list of card states
        for cst in state:
            card = Card(cst['id'], cst['suit'], cst['rank'])
            card.seen = cst['seen']
            card.shown = cst['shown']
            card.is_face_up = cst['is_face_up']
            # add this card to the deck
            self.deck.append(card)

if __name__ == '__main__':

    print('------------------------------------------------------------------------------')
    print('Test creation of a card deck!')
    deck = Deck()
    print(str(deck))
    print(f'length of deck: {len(deck)}')

    print('------------------------------------------------------------------------------')
    print('Test adding a 2nd deck')
    deck2 = Deck(id=1)
    deck += deck2
    print(str(deck))
    print(f'length of deck: {len(deck)}')

    print('------------------------------------------------------------------------------')
    print('Test the shuffle() method')
    deck = Deck()
    deck.shuffle()
    print(f'shuffled deck: {deck}')

    print('------------------------------------------------------------------------------')
    print("Test '[]' and 'in' operators and the index() method")
    card = deck[15]
    if card in deck:
        print(f'{card} is in the deck')
    print(f'{card} is at index={deck.index(card)} in the deck')
    card = Card(1, 'Diamonds', 'A')
    print(f'put {card} at deck[15]')
    deck[15] = card
    print(f'deck: {deck}')
    if card in deck:
        print(f'{card} is in the deck')
    print(f'{card} is at index={deck.index(card)} in the deck')

    print('------------------------------------------------------------------------------')
    print('Test the copy() and sort() methods')
    deck = Deck()
    deck3 = deck.copy()
    print(f'deck: {deck}')
    print(f'deck3: {deck}')
    deck.sort()
    print(f'deck sorted: {deck}')
    print(f'deck3: {deck3}')

    print('------------------------------------------------------------------------------')
    print('Test pop_card() and add_card() methods')
    deck = Deck()
    deck.shuffle()
    print(f'deck: {deck}')
    card = deck.pop_card()
    print(f'deck: {deck}')
    print(f'card: {card}')
    deck.add_card(card)
    print(f'deck: {deck}')
    print('------------------------------------------------------------------------------')
    print('Test removing a card from the deck')
    deck = Deck()
    deck.shuffle()
    card = deck[20]
    print(f'deck: {deck}')
    print(f'card: {card}')
    card2 = deck.remove_card(card)
    print(f'deck: {deck}')
    print(f'card2: {card}')
    print('------------------------------------------------------------------------------')
    print('Get number of different ranks in deck')
    deck = Deck()
    deck.sort()
    print(f'deck: {deck}')
    print(f'number of different ranks in deck: {deck.get_nof_ranks()}')
    deck.pop_card()
    deck.pop_card()
    deck.pop_card()
    deck.pop_card()
    print(f'deck: {deck}')
    print(f'number of different ranks in deck: {deck.get_nof_ranks()}')
    deck.pop_card()
    print(f'deck: {deck}')
    print(f"A's: {deck.get_nof_cards('A')}")
    print(f"K's: {deck.get_nof_cards('K')}")
    print(f"Q's: {deck.get_nof_cards('Q')}")
    print('------------------------------------------------------------------------------')
    print("Test Deck's print method")
    deck = Deck()
    deck.shuffle()
    print('print all cards face up')
    deck.print()
    print('print all cards face down')
    deck.print(False)
    print('turn some cards face up')
    deck[15].face_up()
    deck[16].face_up()
    deck[17].face_up()
    deck.print(False)
    print('------------------------------------------------------------------------------')
    print('Test adding cards to hand')
    deck = Deck()
    deck.shuffle()
    deck.print()
    hand = Deck(empty=True)
    hand.add_card(deck.pop_card())
    hand.add_card(deck.pop_card())
    hand.add_card(deck.pop_card())
    deck.print()
    hand.print()
    print('------------------------------------------------------------------------------')
    print('Test copying a deck')
    deck = Deck()
    deck.shuffle()
    deck.print()
    new_deck = deck.copy()
    new_deck.print()