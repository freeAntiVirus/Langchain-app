
# NOTE: This endpoint is used for testing purposes 
# Context is hardcoded to act as our "Vector Store"
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import asyncio

router = APIRouter()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class GenerateQuestionRequest(BaseModel):
    topic: str
    sample_count: int = 5  # Number of examples to give GPT as context

context = f'''The parabola y = x - 3 2 - 2 is reflected about the y-axis. This is then reflected about
the x-axis.
What is the equation of the resulting parabola?
A. y = ^x + 3h
2 + 2
B. y = ^x - 3h
2 + 2
C. y = -^x + 3h
2 + 2
D. y = -^x - 3h
2 + 2

The diagram shows the graph y = f(x)
Which of the following best represents the graph y = f 2 x - 1 ?

In a particular electrical circuit, the voltage V (volts) across a capacitor is given by
V ^th = 6.5_1 - e– k ti,
where k is a positive constant and t is the number of seconds after the circuit is
switched on.
(a) Draw a sketch of the graph of V ^th, showing its behaviour as t increases.

Suppose the geometric series x + x 2 + x 3 + g has a limiting sum, S.
1 By considering the graph y = -1 - , or otherwise, find the range of possible
x -1
values of S.

The graph y = x2 meets the line y = k (where k > 0) at points P and Q as shown in the
diagram. The length of the interval PQ is L.
y
O x
y = k
y = x2
P Q
x2
 Let a be a positive number. The graph y = meets the line y = k at points S and T. a2
What is the length of ST ?
L A.
a
L B.
a2
C. aL
D. a2
L 

 Sketch the graphs of the functions ƒ( x ) = x − 1 and g( x ) = (1 − x )(3 + x )
showing the x-intercepts. Hence, or otherwise, solve the inequality x − 1 < (1 − x )(3 + x ). 2

The graph of y = ƒ( x ), where ƒ( x ) = a | x − b | + c, passes through the points (3, −5),
(6, 7) and (9, −5) as shown in the diagram.
y
(6, 7)
O x
(3, −5) (9, −5)
(a) Find the values of a, b and c.

b) The line y = m x cuts the graph of y = ƒ( x ) in two distinct places.
Find all possible values of m.
'''

@router.post("/generate-question")
async def generate_question(req: GenerateQuestionRequest):
    topic_id = req.topic
    prompt = f"""
    You are a NSW HSC Mathematics Advanced exam question writer. Here are some example questions on the topic:

    {context}

    Write 5 new, diverse, high-quality exam questions under the same topic.
    

    Instructions:
    - Only return the questions in LaTeX format.
    - Do **NOT** include labels like 'Question X', '3 marks', 'Office Use Only', or ID numbers.
    - Only return the questions – no explanations or commentary
    - DO NOT use LaTeX environments unsupported by MathJax such as:
        - \\begin{{enumerate}}, \\item
        - \\begin{{tabular}}, \\begin{{center}}, etc.
    - Use:
        - \\( ... \\) for inline math
        - \\[ ... \\] or \\begin{{align*}} ... \\end{{align*}} for display math
    """

    # Step 5: Call GPT-4
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You generate mathematics exam questions in LaTeX."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        generated_question = response.choices[0].message.content.strip()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
    return JSONResponse(content={"text": generated_question})

if __name__ == "__main__":

    class DummyRequest:
        def __init__(self, topic, sample_count=3):
            self.topic = topic
            self.sample_count = sample_count

    async def main():
        # Example topic name (must exist in your DB)
        topic_name = "MA-F2"
        req = DummyRequest(topic=topic_name, sample_count=3)
        response = await generate_question(req)
        print("GENERATED", response.body.decode())

    asyncio.run(main())