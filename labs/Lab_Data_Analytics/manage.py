import os
import sys
import subprocess
import venv
import platform

def check_python(osplatform):
    if osplatform == 'windows':
        try:
            result = subprocess.run(["python", "--version"], check=True, stdout=subprocess.PIPE)
            
            python_version = result.stdout.decode().strip()
            print("Python version: " + python_version)
            
            if python_version != "Python 3.11.5":
                print("Please download and install Python version 3.11.5 from the internet.")
                return False
            else:
                print("python Version 3.11.5 is installed and ready to use.")
                return True
            
        except subprocess.CalledProcessError:
            print("Python is not installed. Please download and install Python version 3.11.5 from the internet.")
            return False
            # Add the steps to install Python here
        return True
    else:
        try:
            result = subprocess.run(["python3", "--version"], check=True, stdout=subprocess.PIPE)
            python_version = result.stdout.decode().strip()
            print("Python version: " + python_version)
            if python_version != "Python 3.11.5":
                print("Please download and install Python version 3.11.5 from the internet.")
                return False
            else:
                print("python Version 3.11.5 is installed and ready to use.")
        except subprocess.CalledProcessError:
            print("Python is not installed. Please download and install Python version 3.11.5 from the internet.")
            # Add the steps to install Python here
    return True

def check_pip(osplatform):
    if osplatform == 'windows':
        try:
            subprocess.run(["pip", "--version"], check=True)
            return True
        except subprocess.CalledProcessError:
            print("pip is not installed. Please download and install Python version 3.11.5 from the internet.")
            # Add the steps to install pip here
            return False
    else:
        try:
            subprocess.run(["pip3", "--version"], check=True)
            return True
        except subprocess.CalledProcessError:
            print("pip is not installed. Please download and install Python version 3.11.5 from the internet.")
            # Add the steps to install pip here
            return False
        
def manage_environment(command):
    env_dir = "aoaivenv"
    
    osplatform = platform.system()
    check_python(osplatform.lower())
    check_pip(osplatform.lower())
    
    if osplatform.lower() == 'windows':
        if command == "new":
            os.system(f"python -m venv {env_dir}")
            activate_script = f".\\{env_dir}\\Scripts\\activate"
            os.system(f'cmd /k "{activate_script} && pip install -r requirements.txt"')
        elif command == "activate":
            activate_script = f".\\{env_dir}\\Scripts\\activate"
            os.system(f'cmd /k "{activate_script}"')
        elif command == "deactivate":
            deactivate_script = f".\\{env_dir}\\Scripts\\deactivate.bat"
            os.system(f'cmd /k "{deactivate_script}"')
    else:
        print('non-windows activation')
        if command == "new":
            # venv.create(env_dir, with_pip=True)
            os.system(f"python3 -m venv {env_dir}")
            activate_script = f".//{env_dir}//bin//activate"
            os.system(f"source {activate_script}  && pip3 install -r requirements.txt")
        elif command == "activate":
            activate_script = f".//{env_dir}//bin//activate"
            os.system(f"source {activate_script}")
        elif command == "deactivate":
            deactivate_script = f".//{env_dir}//bin//deactivate.bat"
            os.system(f"{deactivate_script}")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["new", "activate", "deactivate"]:
        print("Usage: python script.py [new|activate|deactivate]")
    else:
        manage_environment(sys.argv[1])