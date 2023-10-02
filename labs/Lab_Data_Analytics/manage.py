import os
import sys
import subprocess
import venv

import platform
print(platform.system())

def check_python():
    try:
        result = subprocess.run(["python", "--version"], check=True, stdout=subprocess.PIPE)
        python_version = result.stdout.decode().strip()
        print("Python version: " + python_version)
        if python_version != "Python 3.11.5":
            print("Please download and install Python version 3.11.5 from the internet.")
        else:
            print("python Version 3.11.5 is installed and ready to use.")
    except subprocess.CalledProcessError:
        print("Python is not installed. Please download and install Python version 3.11.5 from the internet.")
        # Add the steps to install Python here

def check_pip():
    try:
        subprocess.run(["pip", "--version"], check=True)
    except subprocess.CalledProcessError:
        print("pip is not installed. Please download and install Python version 3.11.5 from the internet.")
        # Add the steps to install pip here

def manage_environment(command):
    env_dir = "aoaiLab2"
    check_python()
    check_pip()
    
    if platform.system() == 'Windows':
        
        if command == "new":
            venv.create(env_dir, with_pip=True)
            activate_script = ".\\aoai_lab\\Scripts\\activate"
            os.system(f"cmd /k {activate_script}")
            subprocess.run([f"{env_dir}/Scripts/python", "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        elif command == "activate":
            activate_script = ".\\{env_dir}\\Scripts\\activate"
            os.system(f"cmd /k {activate_script}")
        elif command == "deactivate":
            deactivate_script = ".\\{env_dir}\\Scripts\\deactivate.bat"
            os.system(f"cmd /k {deactivate_script}")
    else:
        if command == "new":
            venv.create(env_dir, with_pip=True)
            activate_script = ".//{env_dir}//bin//activate"
            os.system(f"cmd /k {activate_script}")
            subprocess.run([f"{env_dir}/bin/python", "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        elif command == "activate":
            activate_script = ".//{env_dir}//bin//activate"
            os.system(f"cmd /k {activate_script}")
        elif command == "deactivate":
            deactivate_script = ".//{env_dir}//bin//deactivate.bat"
            os.system(f"cmd /k {deactivate_script}")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["new", "activate", "deactivate"]:
        print("Usage: python script.py [new|activate|deactivate]")
    else:
        manage_environment(sys.argv[1])