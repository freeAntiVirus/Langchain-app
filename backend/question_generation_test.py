from main import generate_question_by_topics
from schemas import GenerateFromTopicsRequest


def main():
    # Create a request object with your desired topics and settings
    req = GenerateFromTopicsRequest(
        topics=[
            "MA-C3: Applications of Differentiation (Year 12)"
        ],
        exemplar_count=5,
        temperature=0.5
    )

    # Call the function directly
    result = asyncio.run(generate_question_by_topics(req))
    print(result)

if __name__ == "__main__":
    import asyncio
    main()