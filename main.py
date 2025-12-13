import os
from dotenv import load_dotenv
from src.executor import root_agent

# 1. Load Keys
load_dotenv()

def run_virtual_cfo():
    print("👠 VIRTUAL CFO: Starting Up...")
    
    # 2. Check for the dataset image
    image_path = "dataset/test_dress_01.jpg"
    if not os.path.exists(image_path):
        print(f"❌ Error: Please place a test image at '{image_path}'")
        return

    print(f"📸 Analyzing Image: {image_path}")

    # 3. Run the Agent Chain
    # We pass the FILE PATH as the input, not a description
    result = root_agent.run(input_str=image_path)
    
    # 4. Output the Result
    print("\n" + "="*50)
    print("💰 FINAL PROFITABILITY REPORT")
    print("="*50)
    print(result)

if __name__ == "__main__":
    run_virtual_cfo()