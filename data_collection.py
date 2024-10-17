import mysql.connector
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from sqlalchemy.orm import sessionmaker
from langchain.embeddings import OpenAIEmbeddings
from credentials import DB_USER, DB_PASSWORD, DB_HOST

# Database connection configuration
db_config = {
    'user': DB_USER,
    'password': DB_PASSWORD,
    'host': DB_HOST,
    'database': 'pdf_data'
}

# Create a connection engine using SQLAlchemy
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/pdf_data")
Session = sessionmaker(bind=engine)
session = Session()

metadata = MetaData()

# Define table for storing text chunks and their embeddings
text_embeddings_table = Table('text_embeddings', metadata,
                              Column('id', Integer, primary_key=True, autoincrement=True),
                              Column('text_chunk', String(2000)),
                              Column('embedding', String(4000)))  # Store embedding as string (can be adjusted)

# Create table if it does not exist
metadata.create_all(engine)


# Function to connect to the MySQL database
def connect_to_db():
    return mysql.connector.connect(**db_config)


# Function to create a table for storing embeddings (if not using SQLAlchemy)
def create_embedding_table():
    connection = connect_to_db()
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS text_embeddings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        text_chunk TEXT,
        embedding TEXT
    )
    """)
    connection.commit()
    cursor.close()
    connection.close()


# Function to vectorize the text chunks using OpenAI embeddings and store in database
def vectorize_and_store(text_chunks):
    embeddings = OpenAIEmbeddings()
    connection = connect_to_db()
    cursor = connection.cursor()

    for chunk in text_chunks:
        # Get the embedding vector for the text chunk
        vector = embeddings.embed_query(chunk)
        vector_str = str(vector)  # Convert the vector to string for storage

        # Insert text chunk and embedding into the database
        query = """
        INSERT INTO text_embeddings (text_chunk, embedding)
        VALUES (%s, %s)
        """
        cursor.execute(query, (chunk, vector_str))
        connection.commit()

    cursor.close()
    connection.close()


# Sample function for processing text chunks (can be called in your main app)
def process_pdf_text_chunks(text_chunks):
    create_embedding_table()  # Ensure table exists
    vectorize_and_store(text_chunks)  # Store embeddings in the database


if __name__ == '__main__':
    # Example usage
    example_text_chunks = ["This is a sample chunk.", "This is another sample chunk."]
    process_pdf_text_chunks(example_text_chunks)
