'''
Statistics class for Shithead game.

The statistics has for each player an entry with:
    - number of times this player was shithead
    - points scored (1 point per player still in the game when player is out)
    - number of games played
    - number of turns played

The statistics are used to evaluate the performance of AI players and to
provide a ranking over multiple games.
Note, that the primary success/failure indicator is the percentage of games a
player ended as shithead.

31.08.2022  Wolfgang Trachsler
'''

from collections import defaultdict
import json

SH_COUNT = 0    # number of times player was shithead
SCORE = 1       # total score
GAMES = 2       # number of games played
TURNS = 3       # total number of turns played

class Statistics():

    def default_val(self):
        '''
        Creates default value for table entry.

        :return:    shit count = 0, total score = 0, number of games = 0,
                    number of turns = 0
        :rtype:     list
        '''
        return [0, 0, 0, 0]

    def __init__(self):
        '''
        initialize the game statistics.
        '''
        # table returns all-0 if key is not in dictionary
        self.table = defaultdict(self.default_val)

    def update(self, name, score, turns):
        '''
        Enters player's score and number of turns used, increments game count.

        :param name:    name of player.
        :type name:     str
        :param score:   number of players still in the game when this player went out,
                        e.g. for  3 players: 1st => 2, 2nd => 1, 3rd (= shithead) => 0.
        :type score:    int
        :param turns:   number of turns played this game.
        :type turns:    int
        '''
        # add score to statistic table entry for this player.
        self.table[name][SCORE] += score   # total score
        self.table[name][TURNS] += turns   # total number of turns
        self.table[name][GAMES] += 1       # number of games played

        # a score of 0 means the player was shithead
        if score == 0:
            self.table[name][SH_COUNT] += 1 # increment the shit count

    def set_stats(self, name, counters):
        '''
        Set the statistic counters for the specified player.

        This either adds a new player with his counters to the statistics, or
        overwrites the current counters of an existing player.

        :param name:        name of player.
        :type name:         str
        :param counters:    shit_count, score, games, turns
        :type counters:     list
        '''
        self.table[name][SH_COUNT] = counters[SH_COUNT]
        self.table[name][SCORE] = counters[SCORE]
        self.table[name][GAMES] = counters[GAMES]
        self.table[name][TURNS] = counters[TURNS]

    def get_stats(self, name):
        '''
        Get the statistic counters for the specified player.

        :param name:    name of player.
        :type name:     str
        :return:        shit_count, score, games, turns
        :rtype:         tuple
        '''
        return (self.table[name][SH_COUNT], self.table[name][SCORE],
                self.table[name][GAMES], self.table[name][TURNS])

    def get_table(self):
        """
        Returns a sorted list of statistics.
        """
        table = []
        total_sh_count = 0
        total_sh_percent = 0
        total_score = 0
        total_games = 0
        total_turns = 0
        # sort the list of table items (= key,value tuples)
        # by value (x[1]) in normal order.
        sorted_table = sorted(self.table.items(), key=lambda x:x[1][SH_COUNT], reverse=False)
        for name,value in sorted_table:
            sh_percent = value[SH_COUNT] / value[GAMES] * 100
            avg_turns = value[TURNS] / value[GAMES]
            entry = [name, f'{value[SH_COUNT]}', f'{sh_percent:.1f}%',
                    f'{value[SCORE]}', f'{value[GAMES]}', f'{value[TURNS]}', f'{avg_turns:.1f}']
            table.append(entry)
            total_sh_count += value[SH_COUNT]
            total_sh_percent += sh_percent
            total_score += value[SCORE]
            total_games = value[GAMES]  # don't sum up
            total_turns += value[TURNS]
        total_avg_turns = total_turns / total_games
        # add entry with totals
        entry = [f'{len(sorted_table)}', f'{total_sh_count}',
                f'{total_sh_percent:.1f}%', f'{total_score}', f'{total_games}',
                f'{total_turns}', f'{total_avg_turns:.1f}']
        table.append(entry)
        return table

    def get_nof_players(self):
        """
        Get the number of players in this statistics.

        :return:    number of players.
        :rtype:     int
        """
        return len(self.table.keys())

    def save(self, filename):
        '''
        Write statistics table to json file.

        :param filename:    name of json file.
        :type filename:     str
        '''
        with open(filename, 'w') as json_file:
            json.dump(self.table, json_file, indent=4)

    def load(self, filename):
        '''
        Loads statistics from json file.

        If file is not present, issues a warning and continues with empty table.

        :param filename:    name of json file.
        :type filename:     str
        '''
        try:
            with open(filename, 'r') as json_file:
                _table = json.load(json_file)
                self.table = defaultdict(self.default_val, _table)
        except OSError as exception:
            print(f"### Warning: couldn't load file {filename}, continue with empty statistic")
            self.table = defaultdict(self.default_val)

    def print(self):
        '''
        Print sorted statistic.
        '''
        # sort the list of table items (= key,value tuples)
        # by value (x[1]) in normal order.
        sorted_table = sorted(self.table.items(), key=lambda x:x[1][SH_COUNT], reverse=False)
        total_games = 0
        total_score = 0
        total_turns = 0
        total_sh_count = 0
        total_sh_percent = 0
        #print sorted table
        print('+--------------------+--------------------+----------+----------+----------+------------+')
        print('| Player             |       Shithead     |    Score |    Games |    Turns | Turns/Game |')
        print('+--------------------+-----------+--------+----------+----------+----------+------------+')
        for name,value in sorted_table:
            sh_percent = value[SH_COUNT] / value[GAMES] * 100
            avg_turns = value[TURNS] / value[GAMES]
            print(f'| {name:<19}|{value[SH_COUNT]:>10} |{sh_percent:>6.1f}% |{value[SCORE]:>9} |{value[GAMES]:>9} |{value[TURNS]:>9} |{avg_turns:11.2f} |')
            total_games = value[GAMES] # don't sum up
            total_score += value[SCORE]
            total_turns += value[TURNS]
            total_sh_count += value[SH_COUNT]
            total_sh_percent += sh_percent
        total_avg_turns = total_turns / total_games
        print('+--------------------+-----------+--------+----------+----------+----------+------------+')
        print(f"| {len(sorted_table):<19}|{total_sh_count:>10} |{total_sh_percent:>6.1f}% |{total_score:>9} |{total_games:>9} |{total_turns:>9} |{total_avg_turns:>11.2f} |")
        print('+--------------------+-----------+--------+----------+----------+----------+------------+')
        print()

    def write_to_file(self, filename):
        '''
        Write human readable statistic table to file.

        :param filename:    name of file.
        :type filename:     str
        '''
        # sort the list of table items (= key,value tuples)
        # by value (x[1]) in normal order.
        sorted_table = sorted(self.table.items(), key=lambda x:x[1][SH_COUNT], reverse=False)
        total_games = 0
        total_score = 0
        total_turns = 0
        total_sh_count = 0
        total_sh_percent = 0
        # write sorted table to file
        with open(filename, 'w') as f:
            f.write('+--------------------+--------------------+----------+----------+----------+------------+\n')
            f.write('| Player             |       Shithead     |    Score |    Games |    Turns | Turns/Game |\n')
            f.write('+--------------------+-----------+--------+----------+----------+----------+------------+\n')
            for name,value in sorted_table:
                sh_percent = value[SH_COUNT] / value[GAMES] * 100
                avg_turns = value[TURNS] / value[GAMES]
                f.write(f'| {name:<19}|{value[SH_COUNT]:>10} |{sh_percent:>6.1f}% |{value[SCORE]:>9} |{value[GAMES]:>9} |{value[TURNS]:>9} |{avg_turns:11.2f} |\n')
                total_games = value[GAMES]  # don't sum up
                total_score += value[SCORE]
                total_turns += value[TURNS]
                total_sh_count += value[SH_COUNT]
                total_sh_percent += sh_percent
            total_avg_turns = total_turns / total_games
            f.write('+--------------------+-----------+--------+----------+----------+----------+------------+\n')
            f.write(f"| {len(sorted_table):<19}|{total_sh_count:>10} |{total_sh_percent:>6.1f}% |{total_score:>9} |{total_games:>9} |{total_turns:>9} |{total_avg_turns:>11.2f} |\n")
            f.write('+--------------------+-----------+--------+----------+----------+----------+------------+\n')


if __name__ == '__main__':

    # create statistics
    stats = Statistics()
    # load statistics from file
    stats.load('ai_test_stats.json')
    # print statistics to terminal
    stats.print()
    tab = stats.get_table()
    print(tab)

