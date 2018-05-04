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

def avg_height(board):
	"""Average height of blocks on the board"""
	total_height = 0
	for height, row in enumerate(reversed(board[1:])):
		for cell in row:
			if _is_block(cell):
				total_height += height
	return total_height / num_blocks(board)

def num_blocks(board):
	"""Number of blocks that exist on the board."""
	c = 0
	for row in board:
		for cell in row:
			if _is_block(cell):
				c += 1
	return c

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
# # # # # # # # # # # # # # # # # # # # # # # # 
NUM_WEIGHTS = 6

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
			mat1[cy+off_y-1	][cx+off_x] += val
	return mat1

def new_board():
	board = [ [ 0 for x in xrange(cols) ]
			for y in xrange(rows) ]
	board += [[ 1 for x in xrange(cols)]]
	return board

###

class DumApp(object):
	def __init__(self):
		# pygame.init()
		# pygame.key.set_repeat(250,25)
		# self.width = cell_size*(cols+6)
		# self.height = cell_size*rows
		# self.rlim = cell_size*cols
		
		# # self.screen = pygame.display.set_mode((self.width, self.height))
		# pygame.event.set_blocked(pygame.MOUSEMOTION)
		# # self.next_stone = tetris_shapes[rand(len(tetris_shapes))]
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

	def drop(self): # check this function carefully
		if not self.gameover and not self.paused:
			# self.score += 1 # if manual else 0
			self.stone_y += 1
			if check_collision(self.board,
			                   self.stone,
			                   (self.stone_x, self.stone_y)):
				#print "1"
				self.board = join_matrixes(self.board,self.stone,(self.stone_x, self.stone_y))
				#print "2"
				# self.new_stone()
				
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
	# things remaining
###

class TetrisApp(object):
	def __init__(self):
		pygame.init()
		pygame.key.set_repeat(250,25)
		self.width = cell_size*(cols+6)
		self.height = cell_size*rows
		self.rlim = cell_size*cols
		self.bground_grid = [[ 8 if x%2==y%2 else 0 for x in xrange(cols)] for y in xrange(rows)]
		
		self.default_font =  pygame.font.Font(
			pygame.font.get_default_font(), 12)
		
		self.screen = pygame.display.set_mode((self.width, self.height))
		pygame.event.set_blocked(pygame.MOUSEMOTION) # We do not need
		                                             # mouse movement
		                                             # events, so we
		                                             # block them.
		self.next_stone = tetris_shapes[rand(len(tetris_shapes))]
		self.init_game()

	def new_stone(self):
		self.stone = self.next_stone[:]
		self.next_stone = tetris_shapes[rand(len(tetris_shapes))]
		self.stone_x = int(cols / 2 - len(self.stone[0])/2)
		self.stone_y = 0
		
		if check_collision(self.board,
		                   self.stone,
		                   (self.stone_x, self.stone_y)):
			self.gameover = True
	
	def init_game(self):
		self.board = new_board()
		self.new_stone()
		self.level = 1
		self.score = 0
		self.lines = 0
		pygame.time.set_timer(pygame.USEREVENT+1, 1000)
	
	def disp_msg(self, msg, topleft):
		x,y = topleft
		for line in msg.splitlines():
			self.screen.blit(
				self.default_font.render(
					line,
					False,
					(255,255,255),
					(0,0,0)),
				(x,y))
			y+=14
	
	def center_msg(self, msg):
		for i, line in enumerate(msg.splitlines()):
			msg_image =  self.default_font.render(line, False,
				(255,255,255), (0,0,0))
		
			msgim_center_x, msgim_center_y = msg_image.get_size()
			msgim_center_x //= 2
			msgim_center_y //= 2
		
			self.screen.blit(msg_image, (
			  self.width // 2-msgim_center_x,
			  self.height // 2-msgim_center_y+i*22))
	
	def draw_matrix(self, matrix, offset):
		off_x, off_y  = offset
		for y, row in enumerate(matrix):
			for x, val in enumerate(row):
				if val:
					pygame.draw.rect(
						self.screen,
						colors[val],
						pygame.Rect(
							(off_x+x) *
							  cell_size,
							(off_y+y) *
							  cell_size, 
							cell_size,
							cell_size),0)
	
	def add_cl_lines(self, n):
		linescores = [0, 40, 100, 300, 1200]
		self.lines += n
		self.score += n # linescores[n] * self.level
		if self.lines >= self.level*6:
			self.level += 1
			newdelay = 1000-50*(self.level-1)
			newdelay = 100 if newdelay < 100 else newdelay
			pygame.time.set_timer(pygame.USEREVENT+1, newdelay)
	
	def move(self, delta_x):
		if not self.gameover and not self.paused:
			new_x = self.stone_x + delta_x
			if new_x < 0:
				new_x = 0
			if new_x > cols - len(self.stone[0]):
				new_x = cols - len(self.stone[0])
			if not check_collision(self.board,
			                       self.stone,
			                       (new_x, self.stone_y)):
				self.stone_x = new_x
	def quit(self):
		self.center_msg("Exiting...")
		pygame.display.update()
		sys.exit()
	
	def drop(self, manual):
		if not self.gameover and not self.paused:
			# self.score += 1 if manual else 0
			self.stone_y += 1
			if check_collision(self.board,self.stone,(self.stone_x, self.stone_y)):
				self.board = join_matrixes(self.board,self.stone,(self.stone_x, self.stone_y))
				self.new_stone()
				cleared_rows = 0
				while True:
					for i, row in enumerate(self.board[:-1]):
						if 0 not in row:
							# for rndom in range(100000000):
							# 	pass
							self.board = remove_row(self.board, i)
							cleared_rows += 1
							break
					else:
						break
				self.add_cl_lines(cleared_rows)
				return True
		return False
	
	def insta_drop(self):
		if not self.gameover and not self.paused:
			while(not self.drop(True)):
				pass
	
	def rotate_stone(self):
		if not self.gameover and not self.paused:
			new_stone = rotate_clockwise(self.stone)
			if not check_collision(self.board,
			                       new_stone,
			                       (self.stone_x, self.stone_y)):
				self.stone = new_stone
	
	def toggle_pause(self):
		self.paused = not self.paused
	
	def start_game(self):
		if self.gameover:
			self.init_game()
			self.gameover = False
 	
	# assign NUM_WEIGHTS, GAMMA

	def reward(self,board,weights):
		ret_val = 0
		# A = -1
		# B = -1
		# C = -1
		# D = -1
		# W = [A,B,C,D]
		ret_vec = [num_holes(board),num_blocks_above_holes(board),num_gaps(board),max_height(board),avg_height(board),sum_adj_diff(board)]
		for i in range(NUM_WEIGHTS):
			ret_val += weights[i]*ret_vec[i]
		return ret_val

	def decide_move(self,cur_board,cur_stone,wts): # to decide the best move based on the current configuration
		max_reward = -1000000 # large negative value
		best_play_rot = 0
		best_play_xval = 0
		for ite in range(4):
			for this_col in range(cols): # two for loops, iterate over all possible rotations and translations
				#print cur_board
				#print "Ending line\n"
				# dont_burn_my_cpu = pygame.time.Clock() --> may need this --> don't know what this does
				# print "Hello there"
				dummy_App = DumApp()
				# dummy_App.board = cur_board[:]
				for x in range(rows):
					for y in range(cols):
						dummy_App.board[x][y] = cur_board[x][y] # copy the board element-wise, this is necessary (accn to python)
				dummy_App.stone = cur_stone[:]
				if this_col > cols - len(cur_stone[0]): # if the column goes ahead, break the translation loop
					break
				dummy_App.stone_x = this_col
				dummy_App.stone_y = 0
				if check_collision( cur_board,cur_stone,(this_col,0) ): # if collision happens with the original configuration of the piece
					continue
				while 1:
					# print "Hi there"
					var2 = dummy_App.drop() # until collision happens (indicated by var2 being True)
					if var2:
						# dummy_App.board = join_matrixes(dummy_App.board,dummy_App.stone,(dummy_App.stone_x,dummy_App.stone_y) )
						# print dummy_App.board
						break
				this_reward = self.reward(dummy_App.board,wts) # calculate reward based on the wts
				# print this_reward
				if this_reward > max_reward:
					max_reward = this_reward
					best_play_rot = ite
					best_play_xval = this_col
			cur_stone = rotate_clockwise(cur_stone)
		# do the best move on the actual board 
		# time.sleep(2)
		# do the best move on the actual board
		for ano in range(best_play_rot):
			self.rotate_stone()
		self.stone_x = best_play_xval

	def run(self,wts):
		key_actions = {
			'ESCAPE':	self.quit,
			# 'LEFT':		lambda:self.move(-1),
			# 'RIGHT':		lambda:self.move(+1),
			# 'DOWN':		lambda:self.drop(True), # drop(True)
			# 'UP':		self.rotate_stone,
			'p':		self.toggle_pause,
			'SPACE':	self.start_game,
			'RETURN':	self.insta_drop
		}
		
		self.gameover = False
		self.paused = False
		
		dont_burn_my_cpu = pygame.time.Clock()
		while 1:
			self.screen.fill((0,0,0))
			if self.gameover:
				self.center_msg("""Game Over!\nYour score: %dPress space to continue""" % self.score)
			else:
				if self.paused:
					self.center_msg("Paused")
				else:
					pygame.draw.line(self.screen,(255,255,255),(self.rlim+1, 0),(self.rlim+1, self.height-1))
					self.disp_msg("Next:", (self.rlim+cell_size,2))
					self.disp_msg("Score: %d\n\nLevel: %d\nLines: %d" % (self.score, self.level, self.lines),(self.rlim+cell_size, cell_size*5))
					self.draw_matrix(self.bground_grid, (0,0))
					self.draw_matrix(self.board, (0,0))
					self.draw_matrix(self.stone,(self.stone_x, self.stone_y))
					self.draw_matrix(self.next_stone,(cols+1,2))
			pygame.display.update()		
			
			# Call some function to simulate all possible rotations and drops of the block ( and the next block )
			# Decide the best one, based on reward of each
			# Play that move ( rotate (function <rotate_stone>) and move (function <move(1) or move(-1)>) to the corresponding column  ) --> then self.drop(False)
			# Do back propagation based on that Reward ? Genetic AI ?

			for event in pygame.event.get():
				if event.type == pygame.USEREVENT+1:
					# self.drop(False)

					if not self.gameover and not self.paused: # the below statement decides the best move based on the current state
						self.decide_move(self.board,self.stone,wts) # also does appropriately call rotate and move
						while 1:
							var = self.drop(True)
							if var:
								break
						#self.quit()
					pass
				elif event.type == pygame.QUIT:
					self.quit()
				elif event.type == pygame.KEYDOWN:
					for key in key_actions:
						if event.key == eval("pygame.K_"+key):
							key_actions[key]()
					
			dont_burn_my_cpu.tick(maxfps)

if __name__ == '__main__':
	App = TetrisApp()
	learned_wts = [-7.98879288e-04,-4.59919586e-03,-9.81677321e-03,-1.01712498e-02,5.93533521e-05,-1.66817345e-03]  # weights learned using try1_LSPI.py
	App.run(learned_wts)