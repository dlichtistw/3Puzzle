import yaml
import re
import itertools
import enum

class Side( enum.Enum ):
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

class Edge( enum.Enum ):
  BASE = 'b'
  RIGHT = 'r'
  LEFT = 'l'

class Tile:
  def __init__( self, base: Face, right: Face, left: Face ):
    self.base = base
    self.right = right
    self.left = left
  
  def __repr__( self ):
    return f'Tile({ self.base },{ self.right },{ self.left })'
  
  def __getitem__( self, edge: Edge ):
    return self.base if edge == Edge.BASE else self.right if edge == Edge.RIGHT else self.left
  
  def rotate( self, rot: int = 1 ):
    r = rot % 3
    if r == 1:
      self.base, self.right, self.left = self.left, self.base, self.right
    elif r == 2:
      self.base, self.right, self.left = self.right, self.left, self.base

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
  yield from itertools.chain( *zip( range( s - 1, -1, -1 ), range( s, 0, -1 ) ) )
  yield from itertools.chain( *zip( range( 1, s + 1 ), range( s ) ) )
  yield s + 1

def print_board( board ):
  l = len( board )
  for r, row, o in zip( itertools.count( l - 1, -1 ), reversed( board ), line_offsets( side( board ) ) ):
    print( '        ' * o, end='' )
    print( *( tile_str( tile, r ) for tile in row ), sep='      ' )

def print_tiles( tiles ):
  for tile in tiles:
    print( tile_str( tile ) )

face_re = re.compile( r'^[1-6][lu]$', flags=re.IGNORECASE )

def check_face( face ):
  if not face_re.match( face ):
    raise RuntimeError( f'Malformed face: {face}' )

def check_tile( tile ):
  if len( tile ) != 3:
    raise RuntimeError( f'Malformed tile: {tile}' )
  for face in tile:
    check_face( face )

def check_board( board ):
  if len( board ) % 6 != 0:
    raise RuntimeError( f'Malformed board: {board}' )
  for face in board:
    check_face( face )

def side( board ):
  return ( len( board ) - 2 ) // 4

def spaces( s ):
  return 6 * s**2

def check_game( board, tiles ):
  if len( tiles ) != spaces( side( board ) ):
    raise RuntimeError( f'Number of tiles ({ len( tiles ) }) does not match the number of free spaces ({ spaces( side( board ) ) }).' )
  counts = { s: [ 0, 0 ] for s in range( 1, 7 ) }
  def counter( face: Face ):
    counts[ face.figure ][ 0 if face.side == Side.LOWER else 1 ] += 1
  for face in board:
    counter( face )
  for tile in tiles:
    for edge in Edge:
      counter( tile[ edge ] )
  for figure, pair in counts.items():
    if pair[ 0 ] != pair[ 1 ]:
      raise RuntimeError( f'Faces mismatch for figure {figure}: {pair[ 0 ]} lower, {pair[ 1 ]} upper parts.' )

def load_tiles( filename ):
  with open( filename, 'r' ) as input:
    tiles = yaml.safe_load( input )
  for tile in tiles:
    check_tile( tile )
  return tuple( Tile( *( Face( s ) for s in tile ) ) for tile in tiles )

def load_board( filename ):
  with open( filename, 'r' ) as input:
    board = yaml.safe_load( input )
  check_board( board )
  return tuple( Face( s ) for s in board )

def init_solution( board ):
  side: int = len( board ) // 6
  lengths = tuple( itertools.chain( ( side, ), *( ( l + 2, l + 1 ) for l in range( side, 2 * side ) ) ) )
  solution = [ [ None ] * l for l in itertools.chain( lengths, reversed( lengths ) ) ]

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

try_count = 0
def try_tile( tile, board, row, col ):
  global try_count
  try_count += 1
  for adj_row, adj_col, edge in adj_spaces( side( board ), row, col ):
    adj = board[ adj_row ][ adj_col ]
    if adj is not None and not tile[ edge ].fits( board[ adj_row ][ adj_col ][ edge ] ):
      return False
  return True

def solve( solution, tiles ):
  if len( tiles ) > 0:
    for row, line in enumerate( solution ):
      for col, space in enumerate( line ):
        if space is None:
          for k, tile in enumerate( tiles ):
            for _ in range( 3 ):
              tile.rotate()
              if try_tile( tile, solution, row, col ):
                solution[ row ][ col ] = tile
                yield from solve( solution, tiles[ :k ] + tiles[ k + 1: ] )
          solution[ row ][ col ] = None
          return
  else:
    yield solution

tiles = load_tiles( 'tiles-2.yaml' )
board = load_board( 'board-2.yaml' )

check_game( board, tiles )

for num, solution in enumerate( solve( init_solution( board ), tiles ), 1 ):
  print( f'--- Solution {num} ---' )
  print_board( solution )
  pass