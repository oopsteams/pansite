# pansite
pan site
# Tools Sql
- Match File Name
    - select id, filename, aliasname from dataitem where panacc = 5 AND isdir = 0  order by filename;
    
- Clear Account

    - accounts, accountext, authuser, ureference, panaccounts
    
- Free

    - tags: free, es/db
    
- lib

    - pip freeze > requirements.txt
    - pip install -r requirements.txt