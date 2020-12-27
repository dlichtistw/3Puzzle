from datetime import timedelta
from enum import Enum
from humanize.number import apnumber, ordinal, intcomma
from humanize.time import naturaldelta
from itertools import chain, count
from math import perm as permutations
from time import perf_counter
from yaml import safe_load as load_yaml
import re
import sys

class Side( Enum ):
  LOWER = 'l'
  l = 'l'
  UPPER = 'u'
  u = 'u'

class Face:
  def __init__( self, code: str ):
    self._figure = int( code[ 0 ] )
    self._side = Side[ code[ 1 ].lower() ]
  
  def __repr__( self ):
    return f'Face(\'{ self._figure }{ self._side.value }\')'
  
  def __str__( self ):
    return f'{ self._figure }{ self._side.value }'
  
  @property
  def figure( self ):
    return self._figure
  
  @property
  def side( self ):
    return self._side
  
  def fits( self, other ):
    return self._figure == other._figure and self._side != other._side

class Edge( Enum ):
  BASE = 'b'
  RIGHT = 'r'
  LEFT = 'l'

class Tile:
  def __init__( self, base: Face, right: Face, left: Face ):
    self._edges = { Edge.BASE: base, Edge.RIGHT: right, Edge.LEFT: left }
  
  def __repr__( self ):
    return f'Tile({ self._edges[ Edge.BASE ] },{ self._edges[ Edge.RIGHT ] },{ self._edges[ Edge.LEFT ] })'
  
  def __getitem__( self, edge: Edge ):
    return self._edges[ edge ]
  
  def rotate( self, rot: int = 1 ):
    r = rot % 3
    if r == 1:
      self._edges[ Edge.BASE ], self._edges[ Edge.RIGHT ], self._edges[ Edge.LEFT ] = self._edges[ Edge.LEFT ], self._edges[ Edge.BASE ], self._edges[ Edge.RIGHT ]
    elif r == 2:
      self._edges[ Edge.BASE ], self._edges[ Edge.RIGHT ], self._edges[ Edge.LEFT ] = self._edges[ Edge.RIGHT ], self._edges[ Edge.LEFT ], self._edges[ Edge.BASE ]
  
  @property
  def base( self ):
    return self._edges[ Edge.BASE ]
  
  @property
  def right( self ):
    return self._edges[ Edge.RIGHT ]
  
  @property
  def left( self ):
    return self._edges[ Edge.LEFT ]

def face_str( face ):
  return '--' if face is None else str( face )

def tile_str( tile, row = 1 ):
  if tile is None:
    return '          '
  else:
    if row % 2 == 1:
      return f'/{ face_str( tile.left ) } { face_str( tile.base ) } { face_str( tile.right ) }\\'
    else:
      return f'\\{ face_str( tile.right ) } { face_str( tile.base ) } { face_str( tile.left ) }/'

def line_offsets( s ):
  yield s + 1
  yield from chain( *zip( range( s - 1, -1, -1 ), range( s, 0, -1 ) ) )
  yield from chain( *zip( range( 1, s + 1 ), range( s ) ) )
  yield s + 1

def print_board( board ):
  l = len( board )
  for r, row, o in zip( count( l - 1, -1 ), reversed( board ), line_offsets( side( board ) ) ):
    print( '        ' * o, end='' )
    print( *( tile_str( tile, r ) for tile in row ), sep='      ' )

def print_tiles( tiles ):
  for tile in tiles:
    print( tile_str( tile ) )

face_re = re.compile( r'^[1-6][lu]$', flags=re.IGNORECASE )

def check_face( face ):
  if not face_re.match( face ):
    raise RuntimeError( f'Malformed face: { face }' )

def check_tile( tile ):
  if len( tile ) != 3:
    raise RuntimeError( f'Malformed tile: { tile }' )
  for face in tile:
    check_face( face )

def check_board( board ):
  if len( board ) % 6 != 0:
    raise RuntimeError( f'Malformed board: { board }' )
  for face in board:
    check_face( face )

def side( board ):
  return ( len( board ) - 2 ) // 4

def spaces( s ):
  return 6 * s**2

def possibilities( board, tiles ):
  s = spaces( side( board ) )
  t = len( tiles )
  return permutations( max( s, t ), min( s, t ) ) * 3**t

def check_game( board, tiles ):
  if len( tiles ) != spaces( side( board ) ):
    raise RuntimeError( f'Malformed game: { len( tiles ) } tiles for { spaces( side( board ) ) } spaces.' )
  counts = { s: [ 0, 0 ] for s in range( 1, 7 ) }
  def faces():
    yield from board
    for tile in tiles:
      yield from ( tile[ edge ] for edge in Edge )
  for face in faces():
    counts[ face.figure ][ 0 if face.side == Side.LOWER else 1 ] += 1
  for figure, pair in counts.items():
    if pair[ 0 ] != pair[ 1 ]:
      raise RuntimeError( f'Malformed game: Figure { figure } has { pair[ 0 ] } lower and { pair[ 1 ] } upper parts.' )

def load_tiles( filename ):
  with open( filename, 'r' ) as input:
    tiles = load_yaml( input )
  for tile in tiles:
    check_tile( tile )
  return tuple( Tile( *( Face( s ) for s in tile ) ) for tile in tiles )

def load_board( filename ):
  with open( filename, 'r' ) as input:
    board = load_yaml( input )
  check_board( board )
  return tuple( Face( s ) for s in board )

def init_solution( board ):
  side: int = len( board ) // 6
  lengths = tuple( chain( ( side, ), *( ( l + 2, l + 1 ) for l in range( side, 2 * side ) ) ) )
  solution = [ [ None ] * l for l in chain( lengths, reversed( lengths ) ) ]

  faces = ( f for f in board )
  solution[ 0 ] = [ Tile( next( faces ), None, None ) for _ in solution[ 0 ] ]
  for i in range( 1, 2 * side, 2 ):
    solution[ i ][ -1 ] = Tile( None, None, next( faces ) )
  for i in range( 2 * side + 2, 4 * side + 1, 2 ):
    solution[ i ][ -1 ] = Tile( None, next( faces ), None )
  solution[ -1 ] = [ Tile( f, None, None ) for f in reversed( [ next( faces ) for _ in solution[ -1 ] ] ) ]
  for i in range( 4 * side, 2 * side + 1, -2 ):
    solution[ i ][ 0 ] = Tile( None, None, next( faces ) )
  for i in range( 2 * side - 1, 0, -2 ):
    solution[ i ][ 0 ] = Tile( None, next( faces ), None )

  return solution

def adj_spaces( side, row, col ):
  base_off = -1 if row % 2 == 1 else 1
  center = 2 * side
  yield row + base_off, col + base_off if row < center else col - base_off if row > center + 1 else col, Edge.BASE
  yield row - base_off, col if row <= center else col - base_off, Edge.RIGHT
  yield row - base_off, col + base_off if row <= center else col, Edge.LEFT

def try_tile( tile, board, row, col ):
  for adj_row, adj_col, edge in adj_spaces( side( board ), row, col ):
    adj = board[ adj_row ][ adj_col ]
    if adj is not None and not tile[ edge ].fits( board[ adj_row ][ adj_col ][ edge ] ):
      return False
  return True

num_try = 0
num_fail = 0
num_try_sol = []
num_fail_sol = []
time_sol = []
def solve( solution, tiles ):
  global num_fail, num_try, num_fail_sol, num_try_sol, time_sol, time_print, time_solve
  if len( tiles ) > 0:
    for row, line in enumerate( solution ):
      for col, space in enumerate( line ):
        if space is None:
          for k, tile in enumerate( tiles ):
            for _ in range( 3 ):
              tile.rotate()
              num_try += 1
              if try_tile( tile, solution, row, col ):
                solution[ row ][ col ] = tile
                yield from solve( solution, tiles[ :k ] + tiles[ k + 1: ] )
          num_fail += 1
          solution[ row ][ col ] = None
          return
  else:
    num_try_sol.append( num_try )
    num_fail_sol.append( num_fail )
    time_sol.append( perf_counter() - time_print - time_solve )
    yield solution

tiles = load_tiles( 'tiles.yaml' )
board = load_board( 'board.yaml' )

check_game( board, tiles )

def number_str( number ):
  if number < 100:
    return apnumber( number )
  elif number < 1_000_000_000:
    return intcomma( int( number ) )
  else:
    return f'{number:.1e}'

print( f'The puzzle has { apnumber( len( tiles ) ) } tiles.' )
print( f'The puzzle has { apnumber( spaces( side( board ) ) ) } spaces.' )
print( f'The puzzle has { number_str( possibilities( board, tiles ) ) } combinations.')

time_solve: float = perf_counter()
time_print: float = 0
for num_sol, solution in enumerate( solve( init_solution( board ), tiles ), 1 ):
  tp = perf_counter()
  print( f'--- Solution { num_sol } ---' )
  print_board( solution )
  time_print += perf_counter() - tp
  pass
time_solve = perf_counter() - time_solve - time_print

def time_str( time ):
  if time < sys.maxsize:
    return naturaldelta( timedelta( seconds=time ), minimum_unit="Microseconds" )
  else:
    return f'{ number_str( time // 3600 // 24 // 365 ) } years'

print( f'I spent { time_str( time_solve ) } solving the puzzle.' )
print( f'I tried { number_str( num_try ) } combinations.' )
print( f'I checked { number_str( num_try / time_solve ) } combinations per second.' )
print( f'I would have needed { time_str( time_solve * possibilities( board, tiles ) / num_try ) } to try all possible combinations.')
print( f'I had { number_str( num_fail ) } failed attempts.' )
print( f'I found { number_str( num_sol ) } solutions.' )
for n, ( y, f, t ) in enumerate( zip( num_try_sol, num_fail_sol, time_sol ), 1 ):
  print( f'I found the { ordinal( n ) } solution after { time_str( t ) } with { number_str( y ) } tries and { number_str( f ) } fails.')
