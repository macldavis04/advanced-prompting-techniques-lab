import ast
import operator
import re

from bedrock_client import invoke_claude_raw


def run_prompt(prompt, system=None, temperature=0.5, max_tokens=500):
    body = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system:
        body["system"] = system
    response = invoke_claude_raw(body)
    return response["content"][0]["text"]


def run_messages(messages, system=None, temperature=0.2, max_tokens=400, stop_sequences=None):
    body = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages
    }
    if system:
        body["system"] = system
    if stop_sequences:
        body["stop_sequences"] = stop_sequences
    response = invoke_claude_raw(body)
    return "".join(block["text"] for block in response["content"] if block["type"] == "text")


def show(label, prompt, system=None, temperature=0.5, max_tokens=500):
    output = run_prompt(prompt, system=system, temperature=temperature, max_tokens=max_tokens)
    print(f"\n=== {label} ===")
    print(f"System: {system}")
    print(f"Temperature: {temperature} | Max tokens: {max_tokens}")
    print(f"Prompt:\n{prompt}")
    print(f"\nOutput:\n{output}")
    return output


EMAIL_THREAD = """
From: Jane Morales (Acme Corp)
To: Deloitte Engagement Team
Subject: Re: Q3 Dashboard Deliverables

Hi team, thanks for the demo on Tuesday. Leadership liked the revenue view,
but they are worried the timeline is slipping. Can you send an updated
delivery date by Friday? Also, our compliance team (contact: Raj Patel)
needs to review the data handling section before final signoff.

From: Mark Chen (Deloitte)
Hi Jane, understood. I'll confirm the new date by Thursday EOD. Priya will
set up the compliance review with Raj next week.

From: Jane Morales (Acme Corp)
Great. One more thing: please add a regional filter to the dashboard. It
does not need to be in this release if it puts the date at risk.
"""


def part1_task1_summarization():
    show(
        "Part 1 Task 1 - Iteration 1: Baseline summary",
        f"Summarize this email thread.\n\n{EMAIL_THREAD}"
    )
    show(
        "Part 1 Task 1 - Iteration 2: Role + constraints + format",
        "Summarize the email thread below for a manager who has 30 seconds to read it.\n"
        "Rules:\n"
        "- Exactly 3 bullet points\n"
        "- Only action items and deadlines\n"
        "- Start each bullet with the owner's name in bold\n"
        "- Do not include greetings or pleasantries\n\n"
        f"{EMAIL_THREAD}",
        system="You are an executive assistant summarizing client correspondence for a Deloitte engagement manager.",
        temperature=0.2
    )


def part1_task2_email_generation():
    show(
        "Part 1 Task 2 - Iteration 1: Baseline email",
        "Write an email to a client about a project delay."
    )
    refined_prompt = (
        "Write an email from Mark Chen (Deloitte engagement lead) to Jane Morales (Acme Corp).\n"
        "Context: the Q3 revenue dashboard will move from October 17 to October 31 because "
        "the source data from Acme's ERP arrived two weeks late. The regional filter Jane "
        "requested will ship in the following release.\n"
        "Constraints:\n"
        "- Under 150 words\n"
        "- Professional and accountable, but do not over-apologize\n"
        "- Include a subject line\n"
        "- End with one clear next step and a proposed meeting time"
    )
    show(
        "Part 1 Task 2 - Iteration 2: Context + constraints, low temperature",
        refined_prompt,
        system="You are a senior consultant who writes concise, client-ready emails.",
        temperature=0.2
    )
    show(
        "Part 1 Task 2 - Iteration 3: Same prompt, high temperature",
        refined_prompt,
        system="You are a senior consultant who writes concise, client-ready emails.",
        temperature=1.0
    )


SALES_DATA = """
region,q1_revenue,q2_revenue,q3_revenue
Northeast,1200000,1150000,980000
Southeast,860000,940000,1050000
Midwest,700000,710000,705000
West,1500000,1620000,1710000
"""


def part1_task3_data_analysis():
    show(
        "Part 1 Task 3 - Iteration 1: Baseline analysis",
        f"Analyze this data.\n\n{SALES_DATA}"
    )
    show(
        "Part 1 Task 3 - Iteration 2: Structured JSON output",
        "Analyze the quarterly revenue data below. Return ONLY a JSON object with these keys:\n"
        '- "fastest_growing_region": string, based on Q1 to Q3 percent change\n'
        '- "declining_regions": array of strings, regions where Q3 is below Q1\n'
        '- "q3_total_revenue": number\n'
        '- "q1_to_q3_change_by_region": object mapping each region to its percent change rounded to 1 decimal\n'
        '- "recommendation": one sentence for the client\n'
        "Do not wrap the JSON in markdown code fences.\n\n"
        f"{SALES_DATA}",
        system="You are a financial analyst. You only report numbers that can be computed from the data provided.",
        temperature=0.0
    )


PART1_REFLECTION = """
Part 1 Reflection
- Adding a role, an audience, and hard constraints (bullet count, word limit,
  owner first) had the biggest effect. The baseline outputs were accurate but
  generic and long; the refined outputs were shorter and organized around what
  the reader actually needs to do.
- Context mattered most for generation. The baseline delay email had to invent
  placeholders like [Project Name] and [New Date]. Giving real names, dates,
  and the reason for the delay removed every placeholder.
- Temperature changed wording, not facts. At 0.2 the email was safe and
  predictable; at 1.0 the subject line and phrasing varied more between runs.
  Low temperature is the right default for client-facing and analytical work.
- Spelling out the JSON keys and types produced output that could be parsed
  directly. The remaining challenge is that a prompt cannot guarantee valid
  JSON every time, and the model can still miscompute a percentage, so the
  numbers should be checked in code. Native tool use fixes the format problem
  but not the math problem.
"""


OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def safe_calculate(expression):
    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
            return OPERATORS[type(node.op)](evaluate(node.operand))
        raise ValueError(f"Unsupported expression: {expression}")

    cleaned = expression.replace(",", "").replace("$", "").strip()
    return round(evaluate(ast.parse(cleaned, mode="eval").body), 4)


REACT_SYSTEM = (
    "You solve problems by interleaving reasoning with actions.\n"
    "Each turn, write exactly one line starting with 'Thought:' and exactly one line starting "
    "with 'Action:', then stop.\n"
    "Available actions:\n"
    "  lookup[key] returns a fact from the firm's reference data\n"
    "  calculate[expression] evaluates arithmetic using numbers, + - * / ** and parentheses\n"
    "  finish[answer] returns your final answer\n"
    "Never write an 'Observation:' line yourself. Observations are provided to you after each action.\n"
    "Do not do arithmetic in your head. Use calculate for every computation."
)

COT_REACT_ADDON = (
    "\nBefore your first Thought, write a 'Plan:' section that reasons step by step about which "
    "facts you need, which calculations you will run, and in what order. "
    "Before calling finish, write a 'Check:' line that verifies the result against your plan."
)


def react(question, facts, plan_first=False, max_steps=10):
    system = REACT_SYSTEM + (COT_REACT_ADDON if plan_first else "")
    available = ", ".join(facts)
    messages = [{"role": "user", "content": f"Question: {question}\nLookup keys available: {available}"}]

    for step in range(1, max_steps + 1):
        reply = run_messages(messages, system=system, stop_sequences=["Observation:"]).strip()
        print(f"\n[Step {step}]\n{reply}")
        messages.append({"role": "assistant", "content": reply})

        match = re.search(r"Action:\s*(\w+)\[(.*)\]", reply, re.DOTALL)
        if not match:
            observation = "No valid action found. Respond with one Thought and one Action."
        else:
            action, argument = match.group(1).lower(), match.group(2).strip()
            if action == "finish":
                return argument
            if action == "lookup":
                observation = facts.get(argument.strip("'\" "), f"No data for '{argument}'. Available keys: {available}")
            elif action == "calculate":
                try:
                    observation = str(safe_calculate(argument))
                except (ValueError, SyntaxError, ZeroDivisionError) as error:
                    observation = f"Calculation error: {error}"
            else:
                observation = f"Unknown action '{action}'. Use lookup, calculate, or finish."

        print(f"Observation: {observation}")
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "No answer reached within the step limit."


INVOICE_QUESTION = (
    "A client invoice of $12,000 is issued. The client pays 40% upfront. The remaining balance "
    "accrues a 1.5% monthly late fee, compounded monthly, for 3 months. At final payment the "
    "client applies a $250 service credit. How much is the final payment?"
)

INVOICE_FACTS = {
    "invoice_total": "$12,000",
    "upfront_payment_percent": "40%",
    "late_fee_policy": "1.5% per month on the unpaid balance, compounded monthly",
    "months_late": "3",
    "service_credit": "$250, applied at final payment after late fees",
}


def part2_task1_invoice():
    show(
        "Part 2 Task 1 - Baseline (answer only)",
        f"{INVOICE_QUESTION}\nGive only the final dollar amount.",
        temperature=0.0,
        max_tokens=50
    )
    show(
        "Part 2 Task 1 - Chain of Thought",
        f"{INVOICE_QUESTION}\n"
        "Think step by step. Number each step, show the formula and the intermediate result for "
        "each step, then give the final answer on its own line starting with 'Answer:'.",
        temperature=0.0,
        max_tokens=600
    )
    print("\n=== Part 2 Task 1 - ReAct (mock lookup + safe calculator) ===")
    answer = react(
        "What is the client's final payment on the overdue invoice? Use the reference data.",
        INVOICE_FACTS
    )
    print(f"\nReAct final answer: {answer}")
    print(f"Verified in Python: ${12000 * 0.6 * 1.015 ** 3 - 250:,.2f}")


OFFICE_DATA = """
Site A (Gulch): 120 seats, $54 per sq ft per year, 9,000 sq ft, $60,000 annual parking cost
Site B (Midtown): 100 seats, $46 per sq ft per year, 8,200 sq ft, $95,000 annual parking cost
Site C (Cool Springs): 140 seats, $38 per sq ft per year, 11,500 sq ft, $20,000 annual parking cost
"""

OFFICE_QUESTION = (
    "Which candidate Nashville office site has the lowest total annual cost per seat, where total "
    "annual cost is rent (price per sq ft times sq ft) plus parking? Give the cost per seat for each site."
)

OFFICE_FACTS = {
    "site_a": "Gulch: 120 seats, $54 per sq ft per year, 9,000 sq ft, $60,000 annual parking cost",
    "site_b": "Midtown: 100 seats, $46 per sq ft per year, 8,200 sq ft, $95,000 annual parking cost",
    "site_c": "Cool Springs: 140 seats, $38 per sq ft per year, 11,500 sq ft, $20,000 annual parking cost",
}


def part2_task2_office_sites():
    show(
        "Part 2 Task 2 - Baseline (answer only)",
        f"{OFFICE_QUESTION}\n{OFFICE_DATA}\nGive only the site name.",
        temperature=0.0,
        max_tokens=50
    )
    show(
        "Part 2 Task 2 - Chain of Thought",
        f"{OFFICE_QUESTION}\n{OFFICE_DATA}\n"
        "Think step by step. For each site, compute rent, then total cost, then cost per seat, "
        "showing each intermediate number. Then compare the three and state the answer on a line "
        "starting with 'Answer:'.",
        temperature=0.0,
        max_tokens=700
    )
    print("\n=== Part 2 Task 2 - Combined CoT + ReAct (plan, act, check) ===")
    answer = react(OFFICE_QUESTION, OFFICE_FACTS, plan_first=True, max_steps=14)
    print(f"\nCoT + ReAct final answer: {answer}")
    for name, seats, rate, sqft, parking in [
        ("Site A", 120, 54, 9000, 60000),
        ("Site B", 100, 46, 8200, 95000),
        ("Site C", 140, 38, 11500, 20000),
    ]:
        print(f"Verified in Python: {name} = ${(rate * sqft + parking) / seats:,.2f} per seat")


PART2_REFLECTION = """
Part 2 Reflection
- Baseline: with the answer forced to a single line, the model has no room to
  work, so multi-step arithmetic like compounding is where it is most likely
  to slip (for example applying simple interest or subtracting the credit
  before the late fees).
- Chain of Thought made every intermediate value visible, which made errors
  easy to spot and usually removed them. The cost is a much longer response.
- ReAct moved the facts and the math out of the model. Every number came from
  a lookup or the calculator, and each step is logged as Thought, Action,
  Observation, so the answer is auditable. Using a stop sequence on
  'Observation:' was necessary to stop the model from inventing its own
  observations.
- Combining them worked best on the office site task. The Plan step made the
  model gather all three sites before calculating, and the Check step caught
  any mismatch before finishing. The tradeoff is more calls and more latency.
- Challenges: parsing free-text actions is fragile, so the loop needs a
  fallback when no action is found and a step limit. The calculator uses an
  AST whitelist instead of eval so model output is never executed as code.
"""


FLAWED_CODE = '''
def process_orders(orders):
    total = 0
    processed = []
    for order in orders:
        price = order["price"] * order["quantity"]
        price = price * order["quantity"]
        total += price
        processed.append(order)

    class _SummaryCache:
        _instance = None
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    cache = _SummaryCache()
    cache.total = total

    discount_formula = orders[0].get("discount_formula", "0")
    discount = eval(discount_formula)
    total = total - discount

    try:
        average = total / len(processed)
    except:
        average = 0

    return {"total": total, "average": average, "processed_count": len(processed)}
'''

CODE_REVIEW_FINDINGS = """
Part 3: Code Review Gauntlet Findings

1. Logic error: price is multiplied by quantity twice. An order of 3 units at
   $10 reports $90 instead of $30. Fix: remove the second multiplication.

2. Over-engineered: a singleton class is built inside the function to hold a
   value that is used once and never read again. Fix: delete it; the local
   variable total already does the job.

3. Security vulnerability: eval() runs discount_formula, which comes from the
   order data. Anyone who controls an order can run arbitrary Python, for
   example "__import__('os').system('...')". Fix: accept a numeric discount
   and validate it with float(), never evaluate input as code.

4. Best practice violation: a bare except swallows every exception, including
   KeyboardInterrupt and real bugs, and silently returns 0. Fix: check for an
   empty list up front (or catch ZeroDivisionError specifically). The function
   also crashes on orders[0] when the list is empty, which the fixed version
   handles.
"""


def process_orders_fixed(orders, discount=0.0):
    if not orders:
        return {"total": 0.0, "average": 0.0, "processed_count": 0}
    discount = float(discount)
    total = sum(order["price"] * order["quantity"] for order in orders) - discount
    return {"total": total, "average": total / len(orders), "processed_count": len(orders)}


def part3_code_review():
    print("\n=== Part 3: Code Review Gauntlet - Flawed Code ===")
    print(FLAWED_CODE)
    print(CODE_REVIEW_FINDINGS)
    sample_orders = [{"price": 10, "quantity": 3}, {"price": 25, "quantity": 2}]
    print("Fixed version on sample orders:", process_orders_fixed(sample_orders, discount=5))
    print("Fixed version on empty list:", process_orders_fixed([]))


PART3_REFLECTION = """
Part 3 Reflection
These issues come from how the model writes code: it pattern-matches to code
it has seen. eval() and bare except are common in tutorials and quick scripts,
so they show up when the model optimizes for "runs without errors." The
singleton reflects a bias toward looking sophisticated, and the duplicated
line is the kind of small slip that still runs and returns a believable
number. Extra scrutiny is most needed anywhere input crosses a trust boundary,
anywhere errors are handled, and in the arithmetic itself, because those
bugs do not crash. They produce wrong answers that look right.
"""


if __name__ == "__main__":
    part1_task1_summarization()
    part1_task2_email_generation()
    part1_task3_data_analysis()
    print(PART1_REFLECTION)

    part2_task1_invoice()
    part2_task2_office_sites()
    print(PART2_REFLECTION)

    part3_code_review()
    print(PART3_REFLECTION)