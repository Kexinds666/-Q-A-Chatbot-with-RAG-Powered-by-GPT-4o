import streamlit as st
import pdfplumber
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from sqlalchemy.orm import sessionmaker
import mysql.connector
from credentials import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME  # Import from credentials.py

from dotenv import load_dotenv
import os

# ****** using free embedding ******
import gensim
from gensim.models.doc2vec import Doc2Vec, TaggedDocument

# Load environment variables from the .env file
load_dotenv('environment.env')

# Retrieve the OpenAI API key from the environment
openai_api_key = os.getenv('OPENAI_API_KEY')

# Check if the key is loaded properly (you can remove this later)
if openai_api_key is None:
    raise ValueError("OpenAI API key not found. Make sure the .env file is correctly loaded.")


# You don’t need to load environment variables since you’re using credentials.py
# Database connection configuration
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# SQLAlchemy setup for connecting to MySQL
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Metadata to manage tables
metadata = MetaData()

# Define the table for storing text chunks and embeddings
text_embeddings_table = Table('text_embeddings', metadata,
                              Column('id', Integer, primary_key=True, autoincrement=True),
                              Column('text_chunk', String(2000)),
                              Column('embedding', String(4000)))

# Create the table if it doesn't exist
metadata.create_all(engine)

# Function to extract text from two-column PDFs, ignoring images
def get_pdf_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf_reader:
        for page in pdf_reader.pages:
            # Extract text column-wise (two-column layout)
            left_bbox = (0, 0, page.width / 2, page.height)
            right_bbox = (page.width / 2, 0, page.width, page.height)

            # Extract text from left and right columns
            left_text = page.within_bbox(left_bbox).extract_text()
            right_text = page.within_bbox(right_bbox).extract_text()

            # Combine text from both columns
            if left_text:
                text += left_text
            if right_text:
                text += right_text
    return text

# Function to split text into 500 character chunks
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=500,
        chunk_overlap=100,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


# Prepare the data
def get_tagged_documents(text_chunks):
    tagged_documents = [TaggedDocument(words=chunk.split(), tags=[str(i)]) for i, chunk in enumerate(text_chunks)]
    return tagged_documents

# Train a Doc2Vec model
def train_doc2vec_model(text_chunks):
    tagged_documents = get_tagged_documents(text_chunks)
    model = Doc2Vec(vector_size=100, window=2, min_count=1, workers=4, epochs=40)
    model.build_vocab(tagged_documents)
    model.train(tagged_documents, total_examples=model.corpus_count, epochs=model.epochs)
    return model

# Function to store embeddings into the MySQL database
def vectorize_and_store(text_chunks):
    # embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    model = train_doc2vec_model(text_chunks)

    connection = mysql.connector.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        database=DB_NAME
    )
    cursor = connection.cursor()

    # for chunk in text_chunks:
    #     # Get the embedding vector for the text chunk
    #     vector = embeddings.embed_query(chunk)
    #     vector_str = str(vector)  # Convert vector to string for database storage
    for i, chunk in enumerate(text_chunks):
        # Get the vector for the chunk
        vector = model.infer_vector(chunk.split())
        vector_str = str(vector.tolist())  # Convert vector to a list and store as string

        # Insert the text chunk and its vector into the database
        query = """
        INSERT INTO text_embeddings (text_chunk, embedding)
        VALUES (%s, %s)
        """
        cursor.execute(query, (chunk, vector_str))
        connection.commit()

    cursor.close()
    connection.close()

# Streamlit App
def main():
    st.set_page_config(page_title="PDF Embedding Processor", page_icon=":robot_face:")

    st.header("Upload and Process PDFs")

    # File uploader for PDFs
    pdf_file = st.file_uploader("Upload your PDF file", type=['pdf'])

    if pdf_file is not None:
        with st.spinner("Extracting text from PDF..."):
            # Step 1: Extract text from the PDF file
            raw_text = get_pdf_text(pdf_file)

            # Step 2: Split the text into chunks of 500 characters
            text_chunks = get_text_chunks(raw_text)

            # Step 3: Vectorize and store the chunks in the database
            vectorize_and_store(text_chunks)

            st.success("Text has been extracted, vectorized, and stored successfully!")

if __name__ == '__main__':
    main()
