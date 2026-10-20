"""Ingest PDF/Markdown with Docling, hierarchical section context, dense+sparse Qdrant vectors."""
import argparse
import hashlib
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding

from app.config import settings


ACCESS = {
    "general": ["doctor", "nurse", "billing_executive", "technician", "admin"],
    "clinical": ["doctor", "admin"],
    "nursing": ["nurse", "admin"],
    "billing": ["billing_executive", "admin"],
    "equipment": ["technician", "admin"],
}


def collection_for(path: Path):
    name = path.parent.name.lower()
    return name if name in ACCESS else "general"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "directory",
        help="Directory organized into collection subfolders",
    )
    args = parser.parse_args()

    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )

    dense_model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

    # Named vectors enable Qdrant's server-side hybrid prefetch/fusion.
    try:
        client.get_collection(settings.qdrant_collection)
    except Exception:
        client.create_collection(
            settings.qdrant_collection,
            vectors_config={
                "dense": models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF
                )
            },
        )

    client.create_payload_index(
        settings.qdrant_collection,
        "collection",
        models.PayloadSchemaType.KEYWORD,
    )
    client.create_payload_index(
        settings.qdrant_collection,
        "access_roles",
        models.PayloadSchemaType.KEYWORD,
    )

    converter = DocumentConverter()
    chunker = HybridChunker(max_tokens=450)
    points = []

    for path in Path(args.directory).rglob("*"):
        if path.suffix.lower() not in {".pdf", ".md", ".markdown"}:
            continue

        coll = collection_for(path)

        doc = converter.convert(str(path)).document
        chunks = chunker.chunk(doc)

        entries = [
            (
                chunker.contextualize(c),
                " / ".join(
                    str(x)
                    for x in getattr(c.meta, "headings", []) or []
                ),
                "table"
                if any(
                    getattr(item, "label", None).value == "table"
                    for item in getattr(c.meta, "doc_items", [])
                )
                else "text",
            )
            for c in chunks
        ]

        texts = [x[0] for x in entries]

        if not texts:
            continue

        dense = dense_model.encode(
            texts,
            normalize_embeddings=True,
        ).tolist()

        sparse = list(sparse_model.embed(texts))

        for i, (txt, section, kind) in enumerate(entries):
            digest = hashlib.sha256(
                f"{path}:{i}:{txt}".encode()
            ).hexdigest()

            points.append(
                models.PointStruct(
                    id=digest[:32],
                    vector={
                        "dense": dense[i],
                        "sparse": models.SparseVector(
                            indices=sparse[i].indices.tolist(),
                            values=sparse[i].values.tolist(),
                        ),
                    },
                    payload={
                        "text": txt,
                        "source_document": path.name,
                        "collection": coll,
                        "access_roles": ACCESS[coll],
                        "section_title": section or "Unsectioned",
                        "chunk_type": kind,
                    },
                )
            )

            if len(points) >= 64:
                client.upsert(
                    settings.qdrant_collection,
                    points,
                )
                points = []

    if points:
        client.upsert(
            settings.qdrant_collection,
            points,
        )

    print("Ingestion complete.")


if __name__ == "__main__":
    main()