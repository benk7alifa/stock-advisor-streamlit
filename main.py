import sys
from pathlib import Path

def run_crew(query: str):
    from stock_advisor_app_001.crew import StockAnalysisCrew
    inputs = {'query': query}
    try:
        crew_result = StockAnalysisCrew().kickoff(inputs=inputs)
        return crew_result
    except Exception as e:
        return f"An unexpected error occurred while running the crew: {e}"

def main():
    print("## Welcome to the AI Stock Trading Advisor ##")
    print("---------------------------------------------")
    print("Enter your stock-related query below. Type 'exit' or 'quit' to stop.")

    while True:
        try:
            user_query = input("\nYour Query: ")
            if user_query.lower() in ['quit', 'exit']:
                print("Exiting application. Goodbye!")
                break
            if not user_query.strip():
                print("Please enter a valid query.")
                continue

            print("\n>>> Analyzing your query, please wait. This may take a few moments...")
            result = run_crew(user_query)
            print("\n--- Advisor's Report ---")
            print(result)
            print("------------------------")

        except KeyboardInterrupt:
            print("\n\nExiting application. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred in the main loop: {e}")

if __name__ == "__main__":
    src_path = Path(__file__).resolve().parents[1]
    if str(src_path) not in sys.path:
        sys.path.append(str(src_path))
    main()