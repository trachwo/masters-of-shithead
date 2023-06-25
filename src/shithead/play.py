'''
Play class for the Shithead game.

Used to specify the possible plays which can be applied to a game state.
    - shuffle the talon.
    - burn some cards (reduce talon to match number of players).
    - deal cards from talon to players.
    - swap hand cards with face up table cards.
    - show the card which lets you be the starting player.
    - play a card (from hand cards, or face down, or face up table cards).
    - take the discard pile.
    - kill the discard pile.
    - refill your hand.
    - end his turn.
    - quit the game.
    - abort the game (in case of AI deadlock)
    - change the DEALER (AI test)

Play objects have of an 'action' and an 'index' attribut.
The 'action' tells which of the above actions to perform.
The 'index' is -1 for most of the plays, but in case of 'GET', PUT', 'SHOW',
'HAND', 'FUP', and 'FDOWN' it indicates which of the cards in the corresponding
list is used in this action.

23.08.2022  Wolfgang Trachsler
'''

ACTIONS = (
    'SHUFFLE',  # shuffle the talon
    'BURN',     # reduce the initial talon to match number of players.
    'DEAL',     # deal 3 face down, 3 face up, and 3 hand cards to each player.
    'GET',      # get face up table card at index on hand.
    'PUT',      # put hand card at index to face up table cards.
    'SHOW',     # show requested card at index to get starting player.
    'HAND',     # play hand card at index
    'FUP',      # play face up card at index
    'FDOWN',    # play face down card at index
    'OUT',      # player has no cards left
    'TAKE',     # take the discard pile on hand
    'KILL',     # kill the discard pile
    'REFILL',   # refill your hand with talon cards
    'END',      # end turn
    'QUIT',     # end the game.
    'ABORT',    # end deadlocked AI-game.
    'DEALER',   # change the shuffling (for AI evaluation round)
)

# class representing a possible shithead play
class Play:
    def __init__(self, action, index=-1):
        '''
        Initializer of Play class.

        Each Play consists of an action which can be performed in the game.
        Some actions ('GET', 'PUT', 'SHOW', 'HAND', 'FUP', and 'FDOWN') use a
        card identified by its index in the corresponding list (hand, face_up,
        or face_down). For all plays not using a card, the index should be set
        to -1.

        :param action:  action performed with this play.
        :type action:   str
        :param index:   index of card used in this Play.
        :type index:    int
        '''
        self.action = action
        self.index = index

    def __str__(self):
        '''
        Convert instance of Play to string.
        '''
        return f'{self.action}:{self.index}'

    def get_state(self):
        '''
        Get dictionary with play attributes.

        :return:        dictionary with play attributes.
        :rtype:         dict
        '''
        state = {}
        state['action'] = self.action
        state['index'] = self.index
        return state
