python -m venv venv
venv/Scripts/activate
pip install google-genai
pip install -r requirements.txt
python main.py init-db
python main.py scrape --source quotes --limit 5


# for db 
python main.py view-db                    # Basic view
python main.py view-db --full             # Full content view
python main.py view-db --limit 5          # Limit results

# search db
python main.py search-db "Einstein"       # Search everything
python main.py search-db "technology"     # Search all fields

# list articles
python main.py list-articles 

# View detailed database contents
python main.py view-db --full

# spl db operations
python db_viewer.py analyze

python db_viewer.py search "John Doe" --field author

# Export everything from db to json
python db_viewer.py export