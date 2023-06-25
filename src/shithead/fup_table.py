'''
Face up table class for Shithead game.

Before the start of the actual Shithead game the players may swap cards beween
their hand and face up table cards. Target should be to get the best
combination of 3 cards out of the 6 hand + face up table cards to the table.
In order to allow the AI players to find the best combination in their cards,
we play a large number of games with random face up table cards, and enter the
result for each combination into the face up table.

29.08.2022  Wolfgang Trachsler
'''

from collections import defaultdict
import json
import pkgutil

SCORE = 0   # total score
GAMES = 1   # number of games
AVG = 2     # average score

# file with face up cards swap table
FUP_TABLE_FILE = 'face_up_table.json'
TEXT_FILE = 'readable_fup_table.txt'

class FupTable():

    def default_val(self):
        '''
        Creates default value for face up table.

        :return:    total score = 0, number of entries = 0, average = 0
        :rtype:     list
        '''
        return [0, 0, 0]

    def __init__(self):
        '''
        initialize the face up table.
        '''
        # table returns 0 if key is not in dictionary
        self.table = defaultdict(self.default_val)
        # initialize dictionary for storing face up table cards per player.
        self.fup_per_player = {}

    def store(self, name, fup):
        '''
        Store the face up table cards of a player.

        :param name:    name of player.
        :type name:     str
        :param fup:     face up table cards of player.
        :type fup:      list
        '''
        _fup = fup[:] # make a copy of list
        _fup.sort()   # sort card list
        # create string of sorted list (without suits, they don't matter)
        fup_str = '-'.join([card.rank for card in _fup])
        # store string of sorted face up table cars under player's name
        self.fup_per_player[name] = fup_str

    def score(self, name, score):
        '''
        Enter result for face up table cards of player to fup table.

        :param name:    name of player.
        :type name:     str
        :param score:   number of players still in the game when this player went out,
                        e.g. for  3 players: 1st => 2, 2nd => 1, 3rd (= shithead) => 0.
        :type score:    int
        '''
        # get face up table cards stored for this player.
        fup_str = self.fup_per_player[name]
        # add score to fup table entry for these face up table cards.
        self.table[fup_str][SCORE] += score   # total score
        self.table[fup_str][GAMES] += 1       # number of times it was scored
        # calculate average score
        self.table[fup_str][AVG] = \
            self.table[fup_str][SCORE] / self.table[fup_str][GAMES]

    def get_score(self, combi):
        '''
        Get the score for the specified card combination from the fup table.

        :param combi:   combination of 3 cards.
        :type combi:    list
        :return:        score found for this combination (not in table => 0).
        :rtype:         int
        '''
        combi.sort()   # should already be sorted, just to be sure.
        combi_str = '-'.join([card.rank for card in combi])
        #print(f'### combi_str: {combi_str}')
        return self.table[combi_str][AVG]


    def find_best(self, cards):
        '''
        Find best 3-of-6 combination as face up table cards.

        Builds all possible 3 card combinations out of the specified 6 cards
        and looks up their score in the face up table. The combination with the
        best score is returned to be used as face up table cards.

        :param cards:   players face up table cards and hand cards.
        :type cards:    list
        :return:        combination of 3 cards with best score.
        :rtype:         list
        '''
        _cards = cards[:] # make a copy of card list
        _cards.sort()   # sort card list
        best = None     # best card combination
        combi = [None, None, None]
        best_score = -1 # score of best card combination

        # generate all possible combinations from 3 out of 6 cards,
        # using the fact that the 3-er combinations as well as the original 6
        # cards are sorted,
        #  i.e we have to consider the following index combinations:
        #  0 1 2, 0 1 3, 0 1 4, 0 1 5, 0 2 3, 0 2 4, 0 2 5, 0 3 4, 0 3 5, 0 4 5,
        #                              1 2 3, 1 2 4, 1 2 5, 1 3 4, 1 3 5, 1 4 5,
        #                                                   2 3 4, 2 3 5, 2 4 5,
        #                                                                 3 4 5
        for idx0 in range(0,4):
            for idx1 in range(1,5):
                for idx2 in range(2,6):
                    if idx0 < idx1 and idx1 < idx2:
                        combi[0] = _cards[idx0]
                        combi[1] = _cards[idx1]
                        combi[2] = _cards[idx2]
                        score = self.get_score(combi)
                        #print(' '.join([str(card) for card in combi]), end=' ')
                        #print(f'score:{score}')
                        if score > best_score:
                            best = combi[:]
                            best_score = score
        #print(' '.join([str(card) for card in best]), end=' ')
        #print(f'best_score:{best_score}')
        return best

    def save(self, filename):
        '''
        Write face up table to json file.

        Writes the dictionary with the face up table card scores to a file.

        :param filename:    name of json file.
        :type filename:     str
        '''
        with open(filename, 'w') as json_file:
            json.dump(self.table, json_file, indent=4)

    def load(self, filename, pkg=False):
        '''
        Loads face up table from json file.

        If file is not present, issues a warning and continues with empty table.

        :param filename:    name of json file.
        :type filename:     str
        :param pkg:         True => load from file in shithead package
        :type pkg:          bool
        '''
        if pkg:
            try:
                data = pkgutil.get_data(__package__, filename)
            except OSError as exception:
                print(f"### Error couldn't load file {TITLE_FILE}")
                return
            _table = json.loads(data)
            self.table = defaultdict(self.default_val, _table)
        else:
            try:
                with open(filename, 'r') as json_file:
                    _table = json.load(json_file)
                    self.table = defaultdict(self.default_val, _table)
            except OSError as exception:
                print(f"### Warning: couldn't load file {filename}, continue with empty face up table")
                self.table = defaultdict(self.default_val)

    def print(self):
        '''
        Print sorted face up table.
        '''
        # sort the list of table items (= key,value tuples)
        # by value (x[1]) in reverse order.
        sorted_table = sorted(self.table.items(), key=lambda x:x[1][AVG], reverse=True)
        total_games = 0
        total_score = 0
        #print sorted table
        print('+----------+----------+----------+----------+')
        print('| Cards    |    Total |    Games |  Average |')
        print('+----------+----------+----------+----------+')
        for fup,value in sorted_table:
            print(f'| {fup:<9}|{value[SCORE]:>9} |{value[GAMES]:>9} |{value[AVG]:>9.2f} |')
            total_games += value[GAMES]
            total_score += value[SCORE]
        total_average = total_score / total_games
        print('+----------+----------+----------+----------+')
        print(f"| {len(sorted_table):<9}|{total_score:>9} |{total_games:>9} |{total_average:>9.2f} |")
        print('+----------+----------+----------+----------+')
        print()

    def write_to_file(self, filename):
        '''
        Write human readable face up table to file.

        :param filename:    name of file.
        :type filename:     str
        '''
        # sort the list of table items (= key,value tuples)
        # by value (x[1]) in reverse order.
        sorted_table = sorted(self.table.items(), key=lambda x:x[1][AVG], reverse=True)
        total_games = 0
        total_score = 0
        #write sorted table to file
        with open(filename, 'w') as f:
            f.write('+----------+----------+----------+----------+\n')
            f.write('| Cards    |    Total |    Games |  Average |\n')
            f.write('+----------+----------+----------+----------+\n')
            for fup,value in sorted_table:
                f.write(f'| {fup:<9}|{value[SCORE]:>9} |{value[GAMES]:>9} |{value[AVG]:>9.2f} |\n')
                total_games += value[GAMES]
                total_score += value[SCORE]
            total_average = total_score / total_games
            f.write('+----------+----------+----------+----------+\n')
            f.write(f"| {len(sorted_table):<9}|{total_score:>9} |{total_games:>9} |{total_average:>9.2f} |\n")
            f.write('+----------+----------+----------+----------+\n')







