from sqlalchemy import Table, Column, MetaData, Text
from migrate import migrate_engine
from migrate.changeset import create_column, drop_column

metadata = MetaData(migrate_engine)

PeopleTable = Table('people', metadata, autoload=True)
questionCol = Column('security_question', Text)
answerCol = Column('security_answer', Text)

def upgrade():
    create_column(questionCol, PeopleTable)
    create_column(answerCol, PeopleTable)

def downgrade():
    drop_column(questionCol, PeopleTable)
    drop_column(answerCol, PeopleTable)
