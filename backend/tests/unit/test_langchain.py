from langchain_core.documents import Document

from app.ingestion.chunkers import SectionChunker, TextChunk
from app.providers.embeddings.jina import JinaEmbeddingProvider
from app.providers.llm import get_chat_model


def test_chunker_to_langchain_documents():
    chunker = SectionChunker()
    chunks = [
        TextChunk(
            chunk_index=0,
            text="Enterprise HR Policy Overview",
            section="Overview",
            page_start=1,
            page_end=1,
            token_count=5,
        ),
        TextChunk(
            chunk_index=1,
            text="Leave Entitlement: 20 days paid leave per annum.",
            section="Leave Policy",
            page_start=1,
            page_end=2,
            token_count=10,
        ),
    ]

    docs = chunker.to_langchain_documents(chunks, base_metadata={"department": "HR", "doc_id": "doc-123"})
    assert len(docs) == 2
    assert isinstance(docs[0], Document)
    assert docs[0].page_content == "Enterprise HR Policy Overview"
    assert docs[0].metadata["department"] == "HR"
    assert docs[0].metadata["section"] == "Overview"
    assert docs[1].metadata["page_end"] == 2


def test_jina_provider_is_langchain_embeddings():
    provider = JinaEmbeddingProvider(api_key="dummy_key", model_name="jina-embeddings-v3")
    # Must adhere to LangChain Embeddings interface
    assert hasattr(provider, "embed_documents")
    assert hasattr(provider, "embed_query")


def test_chat_groq_instance():
    llm = get_chat_model()
    assert llm is not None
    assert hasattr(llm, "invoke")


def test_langchain_loaders_load_file(tmp_path):
    from app.ingestion.loaders import load_documents_with_langchain

    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hello from LangChain document loader!", encoding="utf-8")

    docs = load_documents_with_langchain(txt_file)
    assert len(docs) == 1
    assert "Hello from LangChain" in docs[0].page_content
    assert isinstance(docs[0], Document)
