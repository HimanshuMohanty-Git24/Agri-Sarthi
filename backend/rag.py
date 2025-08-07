import os
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import google.generativeai as genai

class RAGSystem:
    def __init__(self, file_path="soildata.csv"):
        # Check for Google API key for embeddings
        google_api_key = os.getenv("GOOGLE_API_KEY")
        print("🔄 Initializing RAG system...")
        print(f"📋 GOOGLE_API_KEY loaded: {'Yes' if google_api_key else 'No'}")
        
        if not google_api_key:
            print("\n⚠️  --- WARNING ---")
            print("GOOGLE_API_KEY not found in .env file.")
            print("The Soil & Crop Advisor Agent requires Gemini embeddings and will not work without it.")
            print("Please add your Google API key to the .env file.")
            print("---------------\n")
            self.retriever = None
            return
        
        # Configure the generative AI client
        print("🔑 Configuring Google Generative AI...")
        genai.configure(api_key=google_api_key)

        self.file_path = file_path
        self.vector_store_path = "faiss_vector_store"
        
        if not os.path.exists(self.file_path):
            print(f"❌ --- ERROR ---")
            print(f"'{self.file_path}' not found in the backend directory.")
            print("Please make sure the soil data CSV file is present.")
            print("---------------\n")
            self.retriever = None
            return

        # Check if vector store already exists
        if os.path.exists(self.vector_store_path):
            print("📁 Found existing vector store, loading...")
            self.vector_store = self._load_vector_store()
        else:
            print("🏗️  No existing vector store found, creating new one...")
            self.vector_store = self._create_vector_store()
            
        if self.vector_store:
            self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 3})
            print("✅ RAG system initialized successfully!")
        else:
            self.retriever = None
            print("❌ RAG system initialization failed!")

    def _load_vector_store(self):
        """Load existing FAISS vector store"""
        try:
            print("🔄 Loading embeddings model...")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            print("📂 Loading FAISS vector store from disk...")
            vector_store = FAISS.load_local(self.vector_store_path, embeddings, allow_dangerous_deserialization=True)
            print("✅ Vector store loaded successfully!")
            return vector_store
        except Exception as e:
            print(f"⚠️  Error loading existing vector store: {e}")
            print("🏗️  Will create new vector store...")
            return self._create_vector_store()

    def _create_vector_store(self):
        """Loads data from the provided CSV and creates a FAISS vector store using Gemini embeddings."""
        try:
            print("📊 Reading CSV file...")
            df = pd.read_csv(self.file_path)
            print(f"📈 Found {len(df)} rows of soil data")
            
            print("📝 Creating documents...")
            documents = []
            for i, (_, row) in enumerate(df.iterrows()):
                if i % 50 == 0:  # Progress indicator every 50 rows
                    print(f"   Processing row {i+1}/{len(df)}...")
                    
                content = (
                    f"Soil analysis for {row['district']}, {row['state']}:\n"
                    f"- Soil Type: {row['soil_type']}\n"
                    f"- pH Level: {row['ph']}\n"
                    f"- Organic Carbon: {row['organic_carbon']}%\n"
                    f"- Nitrogen (N): {row['nitrogen']} kg/ha\n"
                    f"- Phosphorus (P): {row['phosphorus']} kg/ha\n"
                    f"- Potassium (K): {row['potassium']} kg/ha\n"
                    f"- Average Annual Rainfall: {row['rainfall']} mm\n"
                    f"- Average Temperature: {row['temperature']}°C\n"
                    f"This combination of {row['soil_type']} soil with a pH of {row['ph']} is suitable for specific crops adapted to these conditions."
                )
                doc = Document(page_content=content, metadata={"state": row['state'], "district": row['district']})
                documents.append(doc)

            print("✂️  Splitting documents into chunks...")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            splits = text_splitter.split_documents(documents)
            print(f"📄 Created {len(splits)} text chunks")
            
            print("🧠 Initializing Gemini embedding model...")
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            
            print("🔢 Creating vector embeddings (this may take a few minutes)...")
            print("   Please wait while we process the embeddings...")
            vector_store = FAISS.from_documents(splits, embeddings)
            
            print("💾 Saving vector store to disk for future use...")
            vector_store.save_local(self.vector_store_path)
            
            print("✅ FAISS vector store created and saved successfully!")
            return vector_store
        except Exception as e:
            print(f"❌ Error creating vector store with Gemini embeddings: {e}")
            return None

# Instantiate the RAG system globally so it's ready for the agent
rag_system = RAGSystem()