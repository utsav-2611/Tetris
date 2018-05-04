#!/usr/bin/env python2
#-*- coding: utf-8 -*-

# NOTE FOR WINDOWS USERS:
# You can download a "exefied" version of this game at:
# http://kch42.de/progs/tetris_py_exefied.zip
# If a DLL is missing or something like this, write an E-Mail (kevin@kch42.de)
# or leave a comment on this gist.

# Very simple tetris implementation
# 
# Control keys:
#       Down - Drop stone faster
# Left/Right - Move stone
#         Up - Rotate Stone clockwise
#     Escape - Quit game
#          P - Pause game
#     Return - Instant drop
#
# Have fun!

# Copyright (c) 2010 "Kevin Chabowski"<kevin@kch42.de>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import numpy as np
from random import randrange as rand
from random import randint
import pygame, sys
import time
# The configuration
cell_size =	18
cols =		10
rows =		22
maxfps = 	30

colors = [
(0,   0,   0  ),
(255, 85,  85),
(100, 200, 115),
(120, 108, 245),
(255, 140, 50 ),
(50,  120, 52 ),
(146, 202, 73 ),
(150, 161, 218 ),
(35,  35,  35) # Helper color for background grid
]

# Define the shapes of the single parts
tetris_shapes = [
	[[1, 1, 1],
	 [0, 1, 0]],
	
	[[0, 2, 2],
	 [2, 2, 0]],
	
	[[3, 3, 0],
	 [0, 3, 3]],
	
	[[4, 0, 0],
	 [4, 4, 4]],
	
	[[0, 0, 5],
	 [5, 5, 5]],
	
	[[6, 6, 6, 6]],
	
	[[7, 7],
	 [7, 7]],
]

# # # # # # # # # # # # # # # # # # # # # # # # 
"""These heuristics attempt to assess how favourable a given board is.
The board should already have the dummy 23rd row stripped out.
When the heuristic says "block" it means one individual cell of a stone.

How you weight the different heuristics is up to you. 
Most are designed to indicate bad things, and so should have negative weights.
"""

def _is_block(cell):
	return cell != 0

def _is_empty(cell):
	return cell == 0

def _holes_in_board(board):
	"""A hole is defined as an empty space below a block. 
	The block doesn't have to be directly above the hole for it to count.
	This function identifies any holes and returns them as a [(x,y)]
	"""
	holes = []
	block_in_col = False
	for x in range(len(board[0])):
		for y in range(len(board)):
			if block_in_col and _is_empty(board[y][x]):
				holes.append((x,y))
			elif _is_block(board[y][x]):
				block_in_col = True
		block_in_col = False
	return holes

def num_holes(board):
	"""Number of holes that exist on the board."""
	return len(_holes_in_board(board))

def num_blocks_above_holes(board):
	"""Number of blocks that are placed above holes. Note that the block
	doesn't have to be directly above the hole, a stack of three blocks on
	top of a single hole will give a result of 3."""
	c = 0
	for hole_x, hole_y in _holes_in_board(board):
		for y in range(hole_y-1, 0, -1):
			if _is_block(board[y][hole_x]):
				c += 1
			else:
				break
	return c

def num_gaps(board):
	"""Like holes, but horizontal. Discourages waiting for the magic I-beam piece.
	Need to find block-gap-block sequences. A wall can substitute for a block."""
	gaps = []
	sequence = 0 # 0 = no progress, 1 = found block, 2 = found block-gap, 3 = found block-gap-block (not used)
	board_copy = []

	# Make walls into blocks for simplicity
	for y in range(len(board)):
		board_copy.append([1] + board[y] + [1])

	# Detect gaps
	for y in range(len(board_copy)):
		for x in range(len(board_copy[0])):
			if sequence == 0 and _is_block(board_copy[y][x]):
				sequence = 1
			elif sequence == 1 and _is_empty(board_copy[y][x]):
				sequence = 2
			elif sequence == 2:
				if _is_block(board_copy[y][x]):
					gaps.append(board_copy[y][x-1])
					sequence = 1
				else:
					sequence = 0

	return len(gaps)	

def max_height(board):
	"""Height of the highest block on the board"""
	for idx, row in enumerate(board):
		for cell in row:
			if _is_block(cell):
				return len(board) - idx-1

def num_blocks(board):
	"""Number of blocks that exist on the board."""
	c = 0
	for row in board:
		for cell in row:
			if _is_block(cell):
				c += 1
	return c

def avg_height(board):
	"""Average height of blocks on the board"""
	total_height = 0
	for height, row in enumerate(reversed(board[1:])):
		for cell in row:
			if _is_block(cell):
				total_height += height
	return total_height / num_blocks(board)

def sum_adj_diff(board):
	diff = 0
	done = [0 for i in xrange(cols)]
	height = [0 for i in xrange(cols)]

	for idx, row in enumerate(board):
		for i in range(len(row)):
			if _is_block(row[i]) and done[i] == False:
				done[i] = 1
				height[i] = len(board) - idx - 1
	for i in range(cols-1):
		diff += abs(height[i+1] - height[i])
	return diff

def rotate_clockwise(shape):
	return [ [ shape[y][x]
			for y in xrange(len(shape)) ]
		for x in xrange(len(shape[0]) - 1, -1, -1) ]

def check_collision(board, shape, offset):
	off_x, off_y = offset
	for cy, row in enumerate(shape):
		for cx, cell in enumerate(row):
			try:
				if cell and board[ cy + off_y ][ cx + off_x ]:
					return True
			except IndexError:
				return True
	return False

def remove_row(board, row):
	del board[row]
	return [[0 for i in xrange(cols)]] + board
	
def join_matrixes(mat1, mat2, mat2_off):
	off_x, off_y = mat2_off
	for cy, row in enumerate(mat2):
		for cx, val in enumerate(row):
			try:
				mat1[cy+off_y-1][cx+off_x] += val
			except IndexError:
				pass
	return mat1

def new_board():
	board = [ [ 0 for x in xrange(cols) ]
			for y in xrange(rows) ]
	board += [[ 1 for x in xrange(cols)]]
	return board

###
NUM_WEIGHTS = 6
GAMMA = 0.9  #tried out values

def reward(board,weights):
	ret_val = 0
	ret_vec = [num_holes(board),num_blocks_above_holes(board),num_gaps(board),max_height(board),avg_height(board),sum_adj_diff(board)]
	for i in range(NUM_WEIGHTS):
		ret_val += float(weights[i])*ret_vec[i]
	return ret_val

class DumApp(object):
	def __init__(self):
		self.init_game()

	def init_game(self):
		self.gameover = False
		self.paused = False
		self.board = new_board()
		self.level = 1
		self.score = 0
		self.lines = 0

	def add_cl_lines(self, n):
		linescores = [0, 40, 100, 300, 1200]
		self.lines += n
		self.score += n # linescores[n] * self.level
		if self.lines >= self.level*6:
			self.level += 1

	def rotate_stone(self):
		if not self.gameover and not self.paused:
			new_stone = rotate_clockwise(self.stone)
			if not check_collision(self.board,
			                       new_stone,
			                       (self.stone_x, self.stone_y)):
				self.stone = new_stone

	def drop(self): 
		if not self.gameover and not self.paused:
			self.stone_y += 1
			if check_collision(self.board,self.stone,(self.stone_x, self.stone_y)):
				self.board = join_matrixes(self.board,self.stone,(self.stone_x, self.stone_y))
				cleared_rows = 0
				while True:
					for i, row in enumerate(self.board[:-1]):
						if 0 not in row:
							self.board = remove_row(
							  self.board, i)
							cleared_rows += 1
							break
					else:
						break
				self.add_cl_lines(cleared_rows)
				return True
		return False

	def decide_move(self,cur_board,cur_stone,wts): # < similar to tetris.py >
		max_reward = -1000000 # large negative value
		best_play_rot = 0
		best_play_xval = 0
		for ite in range(4):
			for this_col in range(cols):
				dummy_App = DumApp()
				
				for x in range(rows):
					for y in range(cols):
						dummy_App.board[x][y] = cur_board[x][y]
				dummy_App.stone = cur_stone[:]
				if this_col > cols - len(cur_stone[0]):
					break
				dummy_App.stone_x = this_col
				dummy_App.stone_y = 0
				if check_collision( cur_board,cur_stone,(this_col,0) ):
					continue
				while 1:
					
					var2 = dummy_App.drop()
					if var2:

						break
				this_reward = reward(dummy_App.board,wts)

				if this_reward > max_reward:
					max_reward = this_reward
					best_play_rot = ite
					best_play_xval = this_col
			cur_stone = rotate_clockwise(cur_stone)

		for ano in range(best_play_rot):
			self.rotate_stone()
		self.stone_x = best_play_xval
		while 1: # do this move
			var = self.drop()
			if var:
				break
###

def GenerateRandomBoard():
	rnd = randint(1,20) # number of blocks between 1 and 20 for generating random board configuration
	dummy_game = DumApp()
	for no_stone in range(rnd):
		rndstone = tetris_shapes[rand(len(tetris_shapes))]
		rot = randint(0,3)
		for rotat in range(rot):
			rotate_clockwise(rndstone)
		dummy_game.stone = rndstone
		# rotation also random
		dummy_game.stone_x = randint(0,cols-len(rndstone[0]))
		dummy_game.stone_y = 0
		if check_collision( dummy_game.board,rndstone,(dummy_game.stone_x,0) ):
			return GenerateRandomBoard()
		while 1:
			var2 = dummy_game.drop()
			if var2:
				break
	final_board = dummy_game.board
	return final_board

def LSTDQ_OPT(limit):
	B = np.zeros((NUM_WEIGHTS,NUM_WEIGHTS)) # B = (1/delta) I
	for i in range(NUM_WEIGHTS):
		B[i][i] = 0.0001
	b = np.zeros((NUM_WEIGHTS,1)) # b = zeros vector

	# random initialisation
	cur_wts = [(1.0/2)*randint(-2,-1),(1.0/2)*randint(-2,-1),(1.0/2)*randint(-2,-1),(1.0/2)*randint(-2,-1),(1.0/2)*randint(-2,-1),(1.0/2)*randint(-2,-1)]

	for i in range(limit):
		new_state = GenerateRandomBoard()
		dummy_stone = tetris_shapes[rand(len(tetris_shapes))]
		stone_x = int(cols / 2 - len(dummy_stone[0])/2)
		stone_y = 0
		# Iterate over all the possible actions of this stone
		for rot in range(4):
			rotate_clockwise(dummy_stone)
			for this_col in range(cols):
				dummy_App = DumApp()
				for x in range(rows):
					for y in range(cols):
						dummy_App.board[x][y] = new_state[x][y]
				dummy_App.stone = dummy_stone[:]
				if this_col > cols - len(dummy_stone[0]):
					break
				dummy_App.stone_x = this_col
				dummy_App.stone_y = 0
				if check_collision( new_state,dummy_stone,(this_col,0) ):
					continue
				while 1:
					var2 = dummy_App.drop()
					if var2:
						break
				phi = np.array( [num_holes(dummy_App.board),num_blocks_above_holes(dummy_App.board),num_gaps(dummy_App.board),max_height(dummy_App.board),avg_height(dummy_App.board),sum_adj_diff(dummy_App.board)] )
				sumphi_ = np.array( [0,0,0,0,0,0] )
				leng = NUM_WEIGHTS
				sumReward = 0
				ns_reward = reward(dummy_App.board,cur_wts)

				phi.shape = [phi.shape[0],1]
				sumphi_.shape = [sumphi_.shape[0],1]

				for next_shape in range(len(tetris_shapes)):
					dummy_App2 = DumApp()
					for x in range(rows):
						for y in range(cols):
							dummy_App2.board[x][y] = dummy_App.board[x][y]
					dummy_App2.stone = tetris_shapes[next_shape]
					dummy_App2.stone_x = int(cols / 2 - len(dummy_App2.stone[0])/2)
					dummy_App2.stone_y = 0
					

					dummy_App2.decide_move(dummy_App2.board,dummy_App2.stone,cur_wts)
					phi_ = [num_holes(dummy_App2.board),num_blocks_above_holes(dummy_App2.board),num_gaps(dummy_App2.board),max_height(dummy_App2.board),avg_height(dummy_App2.board),sum_adj_diff(dummy_App2.board)]
					phi_ = [(1.0/7)*phi_[ite] for ite in range(leng)]
					sumphi_ = [sumphi_[ite] + phi_[ite] for ite in range(leng)]
					here_reward = reward(dummy_App2.board,cur_wts)
					sumReward = sumReward + (1.0/7)*( here_reward - ns_reward )
					

				tempsum = [GAMMA*sumphi_[ite] for ite in range(leng)]
				tempsum = np.array(tempsum)
				tempsum.shape = [tempsum.shape[0],1]
				
				trans = np.transpose( phi - tempsum )
				
				numerator = np.dot(B,phi)
				numerator = np.dot(numerator,trans)
				numerator = np.dot(numerator,B)

				denominator = np.dot(trans,B)
				denominator = np.dot(denominator,phi)

				deno = 1.0 + denominator
				diff = (1.0/deno)*numerator

				B = B - diff
				b = b + np.array( [sumReward*phi[ite] for ite in range(leng)] )
		cur_wts = np.dot(B,b)
		print cur_wts

	return cur_wts

def LSPI():
	# epsilon = 0.00001
	limit = 200 # number of random samples : pretty less because we were limited by computation power, yet the results are pretty promising
	weights = LSTDQ_OPT(limit) # fixed
	return weights

wts_calc = LSPI()
print wts_calc