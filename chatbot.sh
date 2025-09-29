#!/bin/bash
# in case the script uses openai then these are important
echo $GRAMPS_DB_LOCATION
#export GRAMPS_AI_MODEL_NAME="openai/gpt-4o"
#export GRAMPS_AI_MODEL_NAME="openai/text-davinci"
#export GRAMPS_AI_MODEL_NAME="openai/text-davinci"
echo "The GEMINI_API_KEY is: $GEMINI_API_KEY"

# Source the configuration file and export its variables to the environment.
# This ensures that variables like GRAMPS_DB_NAME are available to the Python script.
if [ -f ./config.env ]; then
    set -a # Automatically export all variables defined from now on
    source ./config.env
    set +a # Stop automatically exporting
fi
export GRAMPS_AI_MODEL_NAME="non-existing/model" # non existing

#export GRAMPS_AI_MODEL_NAME="gemini/gemini-2.5-flash" # cloud model -very good
#export GRAMPS_AI_MODEL_NAME="gemini/gemini-2.0-flash" # cloud model - good
#export GRAMPS_AI_MODEL_NAME="ollama/gemma3n:latest" # too big for my pc
#export GRAMPS_AI_MODEL_NAME="ollama/gemma3n:e2b" # no tool cals performed
#export GRAMPS_AI_MODEL_NAME="ollama/deepseek-r1:8b" # too big for my pc
#export GRAMPS_AI_MODEL_NAME="ollama/devstral:latest" # too big for my pc
#export GRAMPS_AI_MODEL_NAME="ollama/mistral:latest" # too big for my pc
#export GRAMPS_AI_MODEL_NAME="ollama/cogito:3b" # works - kinda..
#export GRAMPS_AI_MODEL_NAME="ollama/cogito:8b" # works but tricky with memory
#export GRAMPS_AI_MODEL_NAME="ollama/qwen2.5-coder:latest" # pretty good..
#export GRAMPS_AI_MODEL_NAME="ollama/granite3.3:2b" # crashes often on my pc
#export GRAMPS_AI_MODEL_NAME="ollama/qwen2.5-coder:3b" # reasonable
#export GRAMPS_AI_MODEL_NAME="ollama/gemma3:4b"


echo "The OPENAI_API_KEY is: $OPENAI_API_KEY"
echo "The used database is: $GRAMPS_DB_NAME"
# --- Configuration ---
# Set the name of your virtual environment directory
VENV_NAME="venv_chat"

# Set the name of your Python script
PYTHON_SCRIPT="chatbot.py"

# Define the Python package(s) your script needs
# These will be installed in the virtual environment
PYTHON_PACKAGES="litellm gramps PyGObject"

# --- Script Logic ---

echo "--- Setting up Python environment for ${PYTHON_SCRIPT} ---"

# 1. Check if the virtual environment already exists
if [ ! -d "$VENV_NAME" ]; then
    echo "Creating virtual environment: $VENV_NAME"
    # Create the virtual environment using python3
    python3 -m venv --system-site-packages "$VENV_NAME"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment. Do you have python3-venv installed? (Try: sudo apt install python3-venv)"
        exit 1
    fi
else
    echo "Virtual environment '$VENV_NAME' already exists."
fi

# 2. Activate the virtual environment
echo "Activating virtual environment..."
# Check if the activate script exists before sourcing
if [ -f "$VENV_NAME/bin/activate" ]; then
    source "$VENV_NAME/bin/activate"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to activate virtual environment."
        exit 1
    fi
    echo "Virtual environment activated."
else
    echo "Error: Activate script not found in $VENV_NAME/bin/. Virtual environment might be corrupted."
    exit 1
fi

# 3. Install required Python packages into the virtual environment
echo "Installing/Upgrading required Python packages: ${PYTHON_PACKAGES}"
pip install ${PYTHON_PACKAGES}
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python packages. Please check your network connection or package names."
    deactivate # Deactivate before exiting on error
    exit 1
fi

# 4. Run your Python script
echo "--- Running ${PYTHON_SCRIPT} ---"
python "$PYTHON_SCRIPT" # Use 'python' as it points to the venv's python

# 5. Deactivate the virtual environment (optional, but good practice if you want to return to system environment)
echo "--- Script finished. Deactivating virtual environment. ---"
deactivate

echo "Setup and execution complete."
