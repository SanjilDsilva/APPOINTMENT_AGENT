import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize the modern Gemini client
client = genai.Client()

# 1. Define Mock Tools with identical signatures to register the schemas
# This prevents live DB operations during evaluation testing
def check_availability(day: str):
    pass

def book_appointment(day: str, time_slot: str, customer_name: str):
    pass

def cancel_appointment(day: str, time_slot: str):
    pass

# 2. Replicate your agent's system instructions
SYSTEM_INSTRUCTION = """
You are an advanced AI scheduling assistant for a clinic. 
Your job is to manage appointments using the provided tools.
If a user asks an out-of-scope question, politely redirect them to scheduling.
"""

def run_evaluation():
    # Load the Golden Dataset
    with open("eval_dataset.json", "r") as f:
        data = json.load(f)
        
    test_cases = data["test_cases"]
    passed_tests = 0
    total_tests = len(test_cases)
    
    print("=" * 60)
    print("🚀 STARTING AI AGENT EVALUATION PIPELINE")
    print("=" * 60)
    
    # Configure the Gemini runtime environment
    # We use gemini-2.5-flash as the industry benchmark for rapid tool use
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[check_availability, book_appointment, cancel_appointment],
        temperature=0.0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    )
    
    for tc in test_cases:
        print(f"\n🧪 Testing [{tc['id']}]: {tc['description']}")
        print(f"   Input: \"{tc['input']}\"")
        
        # Fire request to the model
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=tc['input'],
            config=config
        )
        
        # Extract function call intent from Gemini's response
        actual_tool = "none"
        actual_args = {}
        
        if response.function_calls:
            # Grab the first function call intended by the model
            call = response.function_calls[0]
            actual_tool = call.name
            # Convert the Gemini structure to a standard Python dictionary
            actual_args = dict(call.args) if call.args else {}
            
        # Evaluation Logic: Validate tool choice and argument extraction
        expected_tool = tc["expected_tool"]
        
        if actual_tool != expected_tool:
            print(f"   ❌ FAIL: Expected tool '{expected_tool}', but got '{actual_tool}'")
            continue
            
        if expected_tool != "none":
            expected_args = tc["expected_args"]
            # Enforce case insensitivity for string arguments if applicable
            mismatch = False
            for key, val in expected_args.items():
                actual_val = actual_args.get(key)
                if str(actual_val).lower() != str(val).lower():
                    print(f"   ❌ FAIL: Argument mismatch on '{key}'. Expected '{val}', got '{actual_val}'")
                    mismatch = True
                    break
            if mismatch:
                continue
                
        print("   ✅ PASS: Correct tool and arguments mapped successfully.")
        passed_tests += 1

    # Print Final Regression Metrics Report
    print("\n" + "=" * 60)
    print("📊 FINAL EVALUATION REPORT")
    print("=" * 60)
    success_rate = (passed_tests / total_tests) * 100
    print(f"Total Tests Run: {total_tests}")
    print(f"Passed:          {passed_tests}")
    print(f"Failed:          {total_tests - passed_tests}")
    print(f"Success Rate:    {success_rate:.1f}%")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()