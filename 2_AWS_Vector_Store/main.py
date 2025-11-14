"""Simple script: clean text, create chunks, embeddings, upload to S3 Vectors, and search."""
import json
import re
import boto3
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from botocore.exceptions import ClientError
import re



def clean_text(text):
    """
    Cleans text by removing HTML tags, JSON-like data, special characters,
    and extra whitespace in a single regex pass.
    """
    if not isinstance(text, str):
        text = str(text)

    # Combine all cleaning into a single regex substitution
    text = re.sub(
        r'<[^>]+>|'                     # Remove HTML tags
        r'\"[a-zA-Z0-9_]+\"\s*:\s*\"(.*?)\"|'  # JSON-like key/value pairs
        r'[\{\}\[\]\"\']|'              # Braces, brackets, quotes
        r'\\[nrt]|'                     # Escaped characters
        r'[^a-zA-Z0-9\s]',              # Special characters
        lambda m: m.group(1) if m.group(1) else ' ',
        text
    )

    # Remove multiple spaces and trim
    return re.sub(r'\s+', ' ', text).strip()





def create_chunks(text, chunk_size=500, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)


def create_index_if_needed(client, bucket, index_name, dimension):
    try:
        existing = {idx['indexName']: idx for idx in client.list_indexes(vectorBucketName=bucket).get('indexes', [])}
        if index_name not in existing or existing[index_name].get('dimension') != dimension:
            if index_name in existing:
                try:
                    client.delete_index(vectorBucketName=bucket, indexName=index_name)
                except:
                    pass
            client.create_index(vectorBucketName=bucket, indexName=index_name, dataType="float32", dimension=dimension, distanceMetric="cosine")
    except:
        pass


def upload_vectors(chunks, embeddings, bucket, index_name, client):
    """Upload chunks and embeddings to S3 Vectors in batches."""
    if not chunks or not embeddings:
        return
    
    vectors = [{
        'key': f"chunk_{i}_{abs(hash(chunk)) % 100000}",
        'data': {'float32': emb},
        'metadata': {
            'text': chunk,  # Store full text
            'chunk_index': i
        }
    } for i, (chunk, emb) in enumerate(zip(chunks, embeddings))]
    
    batch_size = 400
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        try:
            client.put_vectors(
                vectorBucketName=bucket,
                indexName=index_name,
                vectors=batch
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload vectors: {e}")


def search(query_embedding, bucket, index_name, client, top_k=3):
    """Search for similar vectors in S3 Vectors index."""
    if not query_embedding:
        return []
    
    try:
        response = client.query_vectors(
            vectorBucketName=bucket,
            indexName=index_name,
            queryVector={'float32': query_embedding},
            topK=top_k,
            returnMetadata=True,
            returnDistance=True
        )
        
        results = []
        for match in response.get('vectors', []):
            metadata = match.get('metadata', {})
            distance = match.get('distance', 1.0)
            
            results.append({
                'text': metadata.get('text', ''),
                'similarity': max(0.0, 1.0 - distance),
                'id': match.get('key', ''),
                'chunk_index': metadata.get('chunk_index', -1)
            })
        
        return results
    except ClientError as e:
        raise RuntimeError(f"Search failed: {e}")



def delete_index(bucket, index_name, client):
    """Delete an index in S3 Vectors."""
    try:
        client.delete_index(vectorBucketName=bucket, indexName=index_name)
    except ClientError as e:
        raise RuntimeError(f"Failed to delete index: {e}")


def main():
    # Sample text with special characters and JSON objects
    text = """
    LangChain is a framework for developing applications powered by language models! 🚀
    It enables applications that are data-aware and agentic, meaning they can connect 
    a language model to other sources of data and allow it to interact with its environment.
    
    {"framework": "LangChain", "version": "2.0", "features": ["RAG", "Agents", "Chains"]}
    
    The core idea of LangChain is to chain together different components to create 
    more advanced use cases around LLMs. These components include:
    - Models: Different types of language models
    - Prompts: Managing and optimizing prompts
    - Chains: Combining LLMs and prompts in multi-step workflows
    - Agents: LLMs that make decisions about which actions to take
    - Memory: Persisting application state between runs of a chain
    
    [{"type": "integration", "name": "vector stores"}, {"type": "tool", "name": "document loaders"}]
    
    LangChain also provides integrations with various vector stores, document loaders, 
    and other tools that make it easier to build complex applications with language models.
    
    Special characters: @#$%^&*()_+-=[]{}|;':\",./<>?~` 
    Unicode: café, naïve, résumé, 你好, مرحبا
    
    Vector stores are particularly important for retrieval-augmented generation (RAG) 
    applications, where you need to store and retrieve relevant context for your queries.
    
    {"contact": {"email": "info@langchain.com", "phone": "+1-555-0123"}}
    """
    
    cleaned = clean_text(text)
    chunks = create_chunks(cleaned)
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    embeddings = embeddings_model.embed_documents(chunks)
    dimension = len(embeddings[0]) if embeddings else 1536
    
    client = boto3.client('s3vectors', aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)
    
    bucket = S3_BUCKET_NAME
    index_name = "test-index"
    
    create_index_if_needed(client, bucket, index_name, dimension)
    upload_vectors(chunks, embeddings, bucket, index_name, client)
    
    query = "What is LangChain Managing and optimizing prompts?"
    query_embedding = embeddings_model.embed_query(query)
    results = search(query_embedding, bucket, index_name, client, top_k=3)
    
    print("Similarity Results:")
    print("=" * 80)
    for i, r in enumerate(results, 1):
        print(f"\nResult {i} - Similarity: {r['similarity']:.4f}")
        print(f"Text: {r['text']}\n")
    
    delete_index(bucket, index_name, client)
    print(f"Deleted index: {index_name}")


if __name__ == "__main__":
    main()




# For deleting vectors
# try:
#                 while query_attempts < max_attempts:
#                     # Use slightly different random vectors to get different results
#                     random_vector = [random.uniform(-0.1, 0.1) for _ in range(dimension)]
                    
#                     response = manager.client.query_vectors(
#                         vectorBucketName=manager.bucket_name,
#                         indexName=test_index_name,
#                         queryVector={'float32': random_vector},
#                         topK=max_top_k,
#                         returnMetadata=True,
#                         returnDistance=False
#                     )
                    
#                     batch_results = response.get('vectors', [])
#                     if not batch_results:
#                         break
                    
#                     # Add only new results
#                     new_results = [r for r in batch_results if r.get('key') not in seen_keys]
#                     if not new_results:
#                         break
                    
#                     for result in new_results:
#                         seen_keys.add(result.get('key'))
                    
#                     all_results.extend(new_results)
#                     query_attempts += 1
                    
#                     # If we got fewer than max results, we've likely got everything
#                     if len(batch_results) < max_top_k:
#                         break
                
#                 print(f"   Queried {query_attempts} times, found {len(all_results)} total vectors")
                
#                 # Filter by source_id
#                 matching_keys = []
#                 for result in all_results:
#                     metadata = result.get('metadata', {})
#                     if metadata.get('source_id') == test_source_id_1:
#                         matching_keys.append(result.get('key'))
                
#                 print(f"   Found {len(matching_keys)} vectors with source_id={test_source_id_1}")
                
#                 if matching_keys and hasattr(manager.client, 'delete_vectors'):
#                     # Delete in batches
#                     deleted_count = 0
#                     batch_size = 100
#                     for i in range(0, len(matching_keys), batch_size):
#                         batch_keys = matching_keys[i:i + batch_size]
#                         try:
#                             manager.client.delete_vectors(
#                                 vectorBucketName=manager.bucket_name,
#                                 indexName=test_index_name,
#                                 keys=batch_keys
#                             )
#                             deleted_count += len(batch_keys)
#                             print(f"   ✅ Deleted batch {i//batch_size + 1} ({len(batch_keys)} vectors)")
#                         except Exception as e:
#                             print(f"   ⚠️ Failed to delete batch: {e}")
                    
#                     print(f"✅ Deleted {deleted_count} vectors for source_id={test_source_id_1}")
                    
#                     # Wait for deletion to propagate
#                     print("Waiting 2 seconds for deletion to propagate...")
#                     time.sleep(2)
                    
#                     # Verify deletion - search again
#                     results_after = manager.search(query, test_index_name, top_k=10)
#                     print(f"\n✅ Search after deletion - Found {len(results_after)} results")
                    
#                     # Check that file 1 vectors are gone but file 2 vectors remain
#                     file_1_after = [r for r in results_after if r.get('id', '').startswith(f'file_{test_source_id_1}')]
#                     file_2_after = [r for r in results_after if r.get('id', '').startswith(f'file_{test_source_id_2}')]
                    
#                     print(f"   File 1 vectors after deletion: {len(file_1_after)}")
#                     print(f"   File 2 vectors after deletion: {len(file_2_after)}")
                    
#                     if len(file_1_after) == 0 and len(file_2_after) > 0:
#                         print(f"   ✅ Success! File 1 vectors deleted, File 2 vectors remain")
#                     else:
#                         print(f"   ⚠️ Deletion may not have worked as expected")
                    
#                 else:
#                     print(f"⚠️ delete_vectors API not available or no matching vectors found")
#                     print(f"   This is expected if the API doesn't support delete_vectors yet")
                
#             except Exception as e:
#                 print(f"⚠️ Error during deletion test: {e}")
#                 import traceback
#                 traceback.print_exc()
            