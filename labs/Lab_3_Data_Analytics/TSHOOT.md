# Troubleshooting Steps
No two users or machines are the same, and sometimes we encounter unexpected problems. See the scenarios below for troubleshooting steps to resolve common issues.


## Python missing from PATH
> `The term 'python' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.`

This is a common problem where the `python` command is missing from the `PATH`. If you have recently installed via the VS Code extension, try closing all VS Code windows and re-launching before proceeding with troubleshooting.

### Workaround
* Locate your existing Python installation path by using PowerShell: `Get-Command python`

* You can work around the issue by providing the full path to Python in the command. (e.g. `& 'C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\python.exe' --version`)
> Note the leading "invocation operator (&)" which allows paths containing spaces. 

### Fix
You can permanently fix this issue by adding Python to your PATH environment variables. This can be done manually, OR via the builtin package manager:

* Navigate to `Apps and Features` in Windows settings

* Search for `python` and choose `Modify`

* On the second screen, ensure that the "Add Python to environment variables" option is checked, and proceed.

    ![PATH Update](./Images/python-environment-fix.PNG)

### Verify
Confirm that everything is working by running `python --version`


## Streamlit not found
> `The term 'streamlit' is not recognized as the name of a cmdlet, function, script file, or operable program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.`

This is similar to the scenario above, in that the `PATH` needs to be adjusted to include the Python scripts folder. You will likely encounter this error if you have multiple python versions installed, but the fix is ultimately the same.

* Locate the `streamlit` install location: `pip list -v`

* Add the path to your `PATH` environment variable:
    1. Search for `environment` in the start menu
    1. Select "Edit the system environment variables"
    1. Choose `Environment Variables` from the `Advanced` tab
    1. Add a new entry for the path discovered from `pip list -v` to the `Path` variable

    ![PATH Update](./Images/streamlit-path-fix.PNG)

* Confirm the fix by displaying streamlit help:

    ![Streamlit Help](./Images/streamlit-verify.PNG)