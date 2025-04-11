#!/usr/bin/env python3
import os
import sys
import traceback

def main():
    # Create error log file in the user's home directory
    error_log = os.path.expanduser("~/vfmc_launch_error.txt")
    
    try:
        # Figure out the application bundle path
        if getattr(sys, 'frozen', False):
            # We're running from a PyInstaller bundle
            bundle_dir = os.path.dirname(sys.executable)
            # For apps launched from Finder, we need to set the working directory
            # to the bundle's MacOS directory (where the executable lives)
            if os.path.basename(bundle_dir) == 'MacOS':
                os.chdir(os.path.dirname(os.path.dirname(bundle_dir)))  # Go up to the .app level
        
        # Log starting information
        with open(error_log, "w") as f:
            f.write(f"Launcher starting\n")
            f.write(f"Python: {sys.version}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write(f"Arguments: {sys.argv}\n")
            f.write(f"Current directory: {os.getcwd()}\n")
            f.write("Python path:\n")
            for p in sys.path:
                f.write(f"  {p}\n")
        
        # Try import the vfmc module
        with open(error_log, "a") as f:
            f.write("\nImporting vfmc...\n")
        
        import vfmc.app
        
        with open(error_log, "a") as f:
            f.write("Import successful, launching app...\n")
        
        # Run the app
        vfmc.app.main()
        
    except Exception as e:
        with open(error_log, "a") as f:
            f.write(f"\nERROR: {str(e)}\n")
            f.write(traceback.format_exc())
        
        # Display error in dialog if possible
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error launching VFMC")
            msg.setInformativeText(str(e))
            msg.setDetailedText(traceback.format_exc())
            msg.setWindowTitle("Error")
            msg.exec_()
        except:
            pass
        
        # Re-raise the exception
        raise

if __name__ == "__main__":
    main()