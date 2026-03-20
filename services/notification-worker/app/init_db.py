from database import Base, engine
# for making sure we have table on start up
def init_db():
    Base.metadata.create_all(bind=engine)