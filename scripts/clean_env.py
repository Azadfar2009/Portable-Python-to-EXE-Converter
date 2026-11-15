import os
import shutil

def clean_env(env_dir):
    if not os.path.exists(env_dir):
        print(f"Error: {env_dir} not found.")
        return
        
    print(f"Cleaning {env_dir} to reduce size...")
    
    unwanted_dirs = ["__pycache__", "tests", "test", "docs", "examples", "scripts"]
    
    removed_count = 0
    for root, dirs, files in os.walk(env_dir, topdown=False):
        for d in dirs:
            if d.lower() in unwanted_dirs:
                try:
                    shutil.rmtree(os.path.join(root, d))
                    removed_count += 1
                except: pass
                
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                try:
                    os.remove(os.path.join(root, f))
                    removed_count += 1
                except: pass
                
    print(f"Removed {removed_count} unnecessary files/folders.")

if __name__ == "__main__":
    if os.path.basename(os.getcwd()) == "scripts":
        clean_env("../env")
    else:
        clean_env("env")