"""
Monte Carlo Tree Search (MCTS) Node.

Used to implement MCTS for the the end game, i.e. when the stack is empty and
only 2 players are left in the game.

30.05.2024 Wolfgang Trachsler
"""

import numpy as np


# Class representing a node in the search tree.
class MonteCarloNode():
    """
    Class representing a node in the search tree.

    """
    def __init__(self, parent, play, state, unexpanded_plays):
        '''
        Create a new node of the search tree.

        :param parent: parent node.
        :type parent: MonteCarloNode
        :param play: the play which brought us here from the parent node.
        :type play: Play
        :param state: the current state of the game.
        :type state: State
        :param unexpanded_plays: list of plays not yet taken from this state.
        :type unexpanded_plays: list
        '''
        # the action which brought us from the parent node to this node
        self.play = play

        # the current state of the game (each node needs its own copy)
        # deepcopy causes problems in case of multithreading,
        # therefore we use the copy method of the State class.
        self.state = state.copy()

        # Monte Carlo stuff
        self.n_plays = 0    # number of plays with this node
        self.n_wins = 0     # number of wins with this node

        # Tree stuff
        self.parent = parent    # the parent node

        # the name of the current player in the parent node
        # => if the current player in the parent node is the winner of a
        #    simulation, update the win-counter in this node, because the
        #    current player in the parent made the decision to select this
        #    path.
        if self.parent is not None:
            current = self.parent.state.player
            self.parent_player = self.parent.state.players[current].name
        else:
            # the root node has no parent but we set the parent_player attribut
            # to the name of the current player.
            current = self.state.player
            self.parent_player = self.state.players[current].name

        # create the list of children nodes
        # as dictionary using the play string '<action>:<index>' as key.
        # each entry is a dictionary with a 'play' and a 'node' (not yet
        # created) entry.
        self.children = {}
        for unexp_play in unexpanded_plays:
            self.children[str(unexp_play)] = {'play': unexp_play, 'node': None}

    def child_node(self, play):
        '''
        Returns child reached with specified play.

        Uses the string '<action>:<index>' of this play to get the
        corresponding entry in the children list.
        Throws an exception if the play does not exist, or if the corresponding
        child has not been expanded.

        :param play: a legal play available in the current state.
        :type play: Play
        :return: the child node reached with this play.
        :rtype: MonteCarloNode
        '''
        try:
            child = self.children[str(play)]
        except KeyError:
            raise Exception('No such play!')
        if child['node'] is None:
            raise Exception('Child is not expanded!')
        return child['node']

    def expand(self, play, child_state, unexpanded_plays):
        '''
        Create a new child node for a legal play from this state.

        Check if specified play is legal, i.e. it has a corresponding key in
        the children list of this node.
        Create a new node using this node as parent.
        Update the corresponding entry in the children list with the new node.

        :param play: play which leads from parent to child node.
        :type play: Play
        :param child_state: game state after play has been applied to the
                           current state.
        :type child_state: State
        :param unexpanded_plays: list of legal plays available in the child state.
        :type unexpanded_plays: list
        :return: new child node
        :rtype: MontecarloNode
        '''
        # check if specified play is a key for the childrens list
        if str(play) not in self.children.keys():
            raise Exception('No such play!')
        # create a new node
        child_node = MonteCarloNode(self, play, child_state, unexpanded_plays)
        # update the children list entry with the new node
        self.children[str(play)].update({'node': child_node})
        return child_node

    def all_plays(self):
        '''
        Extract all plays from the children list.

        :return: list of plays extracted from children list.
        :rtype: list
        '''
        ret = []
        for child in self.children.values():
            ret.append(child['play'])
        return ret

    def unexpanded_plays(self):
        '''
        Extract all plays leading to an unexpanded node from the children list.

        :return: plays in children list with unexpanded nodes.
        :rtype: list
        '''
        ret = []
        for child in self.children.values():
            if child['node'] is None:
                ret.append(child['play'])
        return ret

    def is_fully_expanded(self):
        '''
        Check if this node has been fully expanded.

        :return: True => no unexpanded children left.
        :rtype: bool
        '''
        for child in self.children.values():
            if child['node'] is None:
                return False
        else:
            return True

    def is_leaf(self):
        '''
        Check if this is a terminal node.

        A terminal node in this context is a node from which no more legal
        plays are possible, It does not include nodes, there one of the players
        has won the game.
        !!! NOTE !!!
        This is not possible in a game of Shithead.
        There are no patts in Shithead.

        :return: True => no more legal plays possible.
        :rtype: bool
        '''
        if self.children:
            return False
        else:
            return True     # not possible !!! TODO Exception ???

    def get_ucb1(self, bias_param, adjust_ucb1=False):
        '''
        Calculate Upper Confidence Bound 1 for this node.

        This provides the heuristics for finding optimal paths through the
        search tree.
        The exploitation term makes nodes preferable which have already been
        used in a lot of wins, while the exploration term makes nodes
        preferable which have not been used a lot.

        :param bias_param:   usually sqrt(2).
        :type bias_param:    float.
        :param adjust_ucb1: True => parent-plays + 1 for UCB1 calculation.
        :type adjust_ucb1:  bool
        :return:            Upper Confidence Bound 1.
        :rtype:             float.
        '''
        if self.n_plays == 0:
            return 0
        # exploitation term: grows the more this node has been involved in wins
        exploitation = self.n_wins / self.n_plays
        # exploration term: grows the less a node has been selected
        if adjust_ucb1:
            # during backpropagation the parent node is updated after the child
            ln_sp = np.log(self.parent.n_plays + 1)
        else:
            ln_sp = np.log(self.parent.n_plays)
        exploration = np.sqrt(bias_param * ln_sp / self.n_plays)
        # return the upper confidence bound 1
        return exploitation + exploration

    def print(self, adjust_ucb1=False):
        '''
        Print information about this node.

        :param adjust_ucb1: True => parent-plays + 1 for UCB1 calculation.
        :type adjust_ucb1:  bool
        '''
        self.state.print()
        current_player = self.state.players[self.state.player].name

        print(f'Play into this node: {self.parent_player} - {str(self.play)}')
        print(f'\n{current_player} unexpanded plays:')
        for play in self.unexpanded_plays():
            print(f'\t{str(play)}')

        print(f'\n{current_player} expanded plays:')
        for play in self.children.keys():
            if self.children[play]['node'] is not None:
                print(f'\t{str(play)}')

        print(f'\nn_plays: {self.n_plays}')
        print(f'n_wins: {self.n_wins}')
        if self.parent is not None:
            # UCB1 can only be calculated for nodes below the root node
            # parent-plays + 1 if UCB1 is calculated during backpropagation
            # since child is updated before parent.
            print(f'UCB1: {self.get_ucb1(np.sqrt(2), adjust_ucb1)}')
