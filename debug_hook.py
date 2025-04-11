import sys
import os
import traceback

# Create simple log file immediately
with open(os.path.expanduser('~/vfmc_startup.txt'), 'w') as f:
    f.write("App starting\n")
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Executable: {sys.executable}\n")
    f.write("Python path:\n")
    for p in sys.path:
        f.write(f"  {p}\n")
    
    f.write("\nWorking directory: " + os.getcwd() + "\n")
    
    # Try to import key modules and log results
    f.write("\nTrying imports:\n")
    for module_name in ['PyQt5', 'PyQt5.QtWidgets', 'PyOpenGL', 'vfmc', 'vfmc_core']:
        try:
            __import__(module_name)
            f.write(f"  ✓ {module_name} imported successfully\n")
        except Exception as e:
            f.write(f"  ✗ {module_name} failed: {str(e)}\n")
            f.write(f"    {traceback.format_exc()}\n")