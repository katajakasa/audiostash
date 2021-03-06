"""Initial tables

Revision ID: d834a25a010
Revises: 
Create Date: 2015-11-04 18:47:46.445816

"""

from alembic import op, context
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd834a25a010'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('artist',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cover',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('directory',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('directory', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('log',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entry', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('playlist',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('setting',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=32), nullable=True),
    sa.Column('value', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=32), nullable=True),
    sa.Column('password', sa.String(length=255), nullable=True),
    sa.Column('level', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    op.create_table('album',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=True),
    sa.Column('artist', sa.Integer(), nullable=True),
    sa.Column('cover', sa.Integer(), nullable=True),
    sa.Column('is_audiobook', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['artist'], ['artist.id'], ),
    sa.ForeignKeyConstraint(['cover'], ['cover.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('session',
    sa.Column('key', sa.String(length=32), nullable=False),
    sa.Column('user', sa.Integer(), nullable=True),
    sa.Column('start', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user'], ['user.id'], ),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('track',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file', sa.String(length=255), nullable=True),
    sa.Column('type', sa.String(length=8), nullable=True),
    sa.Column('bytes_len', sa.Integer(), nullable=True),
    sa.Column('bytes_tc_len', sa.Integer(), nullable=True),
    sa.Column('album', sa.Integer(), nullable=True),
    sa.Column('dir', sa.Integer(), nullable=True),
    sa.Column('artist', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=128), nullable=True),
    sa.Column('track', sa.Integer(), nullable=True),
    sa.Column('disc', sa.Integer(), nullable=True),
    sa.Column('date', sa.String(length=16), nullable=True),
    sa.Column('genre', sa.String(length=32), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['album'], ['album.id'], ),
    sa.ForeignKeyConstraint(['artist'], ['artist.id'], ),
    sa.ForeignKeyConstraint(['dir'], ['directory.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('playlistitem',
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.Column('updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('track', sa.Integer(), nullable=True),
    sa.Column('playlist', sa.Integer(), nullable=True),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['playlist'], ['playlist.id'], ),
    sa.ForeignKeyConstraint(['track'], ['track.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    data_upgrades()
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('playlistitem')
    op.drop_table('track')
    op.drop_table('session')
    op.drop_table('album')
    op.drop_table('user')
    op.drop_table('setting')
    op.drop_table('playlist')
    op.drop_table('log')
    op.drop_table('directory')
    op.drop_table('cover')
    op.drop_table('artist')

    data_downgrades()
    ### end Alembic commands ###


def data_upgrades():
    op.execute("INSERT INTO `cover` (`deleted`, `updated`, `id`, `file`) VALUES ('0', '2015-01-01 00:00:00', '1', NULL)")
    op.execute("INSERT INTO `artist` (`deleted`, `updated`, `id`, `name`) VALUES ('0', '2015-01-01 00:00:00', '1', 'Unknown')")
    op.execute("INSERT INTO `album` (`deleted`, `updated`, `id`, `title`, `artist`, `cover`, `is_audiobook`) VALUES ('0', '2015-01-01 00:00:00', '1', 'Unknown', '1', '1', '0');")
    op.execute("INSERT INTO `playlist` (`deleted`, `updated`, `id`, `name`) VALUES ('0', '2015-01-01 00:00:00', '1', 'Scratchpad');")


def data_downgrades():
    op.execute("delete from cover where id=1")
    op.execute("delete from artist where id=1")
    op.execute("delete from album where id=1")
    op.execute("delete from playlist where id=1")
