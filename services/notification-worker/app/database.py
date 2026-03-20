from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# connect to the same PostgreSQL service through Docker Compose network
DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/booking_db"

# engine is the core object that knows how to talk to the database
engine = create_engine(DATABASE_URL)

# sessionLocal is not a database session itself
# it is a function-like factory used to create new Session objects
# each Session is used to query, insert, update, delete, and manage transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# base class for defining ORM models
Base = declarative_base()