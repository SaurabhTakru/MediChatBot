"""Measured comparison of dense-only vs hybrid Dense+BM25+RRF retrieval."""

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding

from app.config import settings
from app.security import COLLECTIONS


DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"

CANDIDATE_K = 10


# Replace the relevant_sources values with the actual source documents
# that you determine are relevant for each question.
#
# Example:
# "relevant_sources": {"claim_submission_guide.md"}
#
# Leave empty initially if you want to use the script first to inspect
# the retrieved documents.
EVALUATION_CASES = [
    {
        "question": "How do I submit a claim?",
        "role": "billing_executive",
        "relevant_sources": {
            "claim_submission_guide.md",
        },
    },
    {
        "question": "What information is required for claim submission?",
        "role": "billing_executive",
        "relevant_sources": {
            "claim_submission_guide.md",
        },
    },
    {
        "question": "What is the procedure for handling a maintenance issue?",
        "role": "technician",
        "relevant_sources": {
            "equipment_manual.pdf",
        },
    },
    {
        "question": "What should a nurse do when handling a patient-related procedure?",
        "role": "nurse",
        "relevant_sources": {
            "icu_nursing_procedures.pdf",
            "infection_control.pdf",
        },
    },
    {
        "question": "What clinical guidelines are available?",
        "role": "doctor",
        "relevant_sources": {
            "treatment_protocols.pdf",
            "diagnostic_reference.pdf",
            "drug_formulary.pdf",
        },
    },
]


def dense_model():
    return SentenceTransformer(DENSE_MODEL)


def sparse_model():
    return SparseTextEmbedding(model_name=SPARSE_MODEL)


def qdrant():
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


def access_filter(role: str):
    allowed = COLLECTIONS[role]

    return models.Filter(
        must=[
            models.FieldCondition(
                key="collection",
                match=models.MatchAny(any=allowed),
            ),
            models.FieldCondition(
                key="access_roles",
                match=models.MatchValue(value=role),
            ),
        ]
    )


def dense_only(question: str, role: str, limit: int = CANDIDATE_K):
    """Retrieve using dense vectors only."""

    dense = dense_model().encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    response = qdrant().query_points(
        collection_name=settings.qdrant_collection,
        query=dense,
        using="dense",
        query_filter=access_filter(role),
        limit=limit,
        with_payload=True,
    )

    return response.points


def hybrid(question: str, role: str, limit: int = CANDIDATE_K):
    """Retrieve using the same Dense + BM25 + RRF pipeline as the application."""

    dense = dense_model().encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    sparse_vec = list(
        sparse_model().embed([question])
    )[0]

    response = qdrant().query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            models.Prefetch(
                query=dense,
                using="dense",
                limit=limit,
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_vec.indices.tolist(),
                    values=sparse_vec.values.tolist(),
                ),
                using="sparse",
                limit=limit,
            ),
        ],
        query=models.FusionQuery(
            fusion=models.Fusion.RRF
        ),
        query_filter=access_filter(role),
        limit=limit,
        with_payload=True,
    )

    return response.points


def source_names(points):
    return [
        (point.payload or {}).get(
            "source_document",
            "unknown",
        )
        for point in points
    ]


def relevant_count(sources, relevant_sources):
    if not relevant_sources:
        return None

    return sum(
        1
        for source in sources
        if source in relevant_sources
    )


def main():
    print("=" * 80)
    print("DENSE-ONLY VS HYBRID RETRIEVAL EVALUATION")
    print("=" * 80)

    dense_hits = 0
    hybrid_hits = 0
    evaluated_cases = 0

    for index, case in enumerate(EVALUATION_CASES, start=1):
        question = case["question"]
        role = case["role"]
        relevant_sources = case["relevant_sources"]

        dense_points = dense_only(question, role)
        hybrid_points = hybrid(question, role)

        dense_sources = source_names(dense_points)
        hybrid_sources = source_names(hybrid_points)

        print()
        print(f"Question {index}: {question}")
        print(f"Role: {role}")

        print()
        print("Dense-only Top 10:")
        for rank, source in enumerate(dense_sources, start=1):
            print(f"  {rank:2}. {source}")

        print()
        print("Hybrid Dense + BM25 + RRF Top 10:")
        for rank, source in enumerate(hybrid_sources, start=1):
            print(f"  {rank:2}. {source}")

        if relevant_sources:
            dense_relevant = relevant_count(
                dense_sources,
                relevant_sources,
            )

            hybrid_relevant = relevant_count(
                hybrid_sources,
                relevant_sources,
            )

            evaluated_cases += 1

            if dense_relevant > 0:
                dense_hits += 1

            if hybrid_relevant > 0:
                hybrid_hits += 1

            print()
            print(f"Expected relevant sources: {sorted(relevant_sources)}")
            print(
                f"Dense relevant documents in Top 10: "
                f"{dense_relevant}"
            )
            print(
                f"Hybrid relevant documents in Top 10: "
                f"{hybrid_relevant}"
            )

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if evaluated_cases:
        dense_recall = dense_hits / evaluated_cases
        hybrid_recall = hybrid_hits / evaluated_cases

        print(f"Evaluated questions: {evaluated_cases}")
        print(
            f"Dense-only Recall@10: "
            f"{dense_hits}/{evaluated_cases} "
            f"({dense_recall:.1%})"
        )
        print(
            f"Hybrid Recall@10: "
            f"{hybrid_hits}/{evaluated_cases} "
            f"({hybrid_recall:.1%})"
        )

        improvement = hybrid_recall - dense_recall

        print(
            f"Hybrid improvement: "
            f"{improvement:+.1%}"
        )
    else:
        print("No relevance labels have been added yet.")
        print(
            "Use the retrieved source documents above to populate "
            "'relevant_sources' for each evaluation question."
        )


if __name__ == "__main__":
    main()